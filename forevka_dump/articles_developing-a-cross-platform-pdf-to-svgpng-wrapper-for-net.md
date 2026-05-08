# Developing a Cross-Platform PDF-to-SVG/PNG Wrapper for .NET

> Source: https://forevka.dev/articles/developing-a-cross-platform-pdf-to-svgpng-wrapper-for-net/

---

# PDF->SVG/PNG: fusing Poppler’s battle-tested PDF engine with Cairo’s SVG output surface, then wraps the native glue in a tidy C# API via [DllImport] 

Building a Cross-Platform PDF-to-SVG Bridge for .NET

## The business problem

A few weeks ago a customer asked for **PDF pages to appear inside a generated DOCX report**.

  * Converting each page to **raster images (PNG/JPEG)** ballooned the file size and slowed down the pipeline.

  * Embedding raw PDF was out - the Word rendering engine would not display it reliably.




> **Goal:** _“If a page can be expressed as scalable vector graphics, embed it as SVG; otherwise fall back to a single PNG bitmap.”_

That single sentence drove the rest of the journey.

## Designing the native engine

### Choosing the tools

  * **Poppler** \- mature PDF parser / renderer.

  * **Cairo** \- can paint to many back-ends, including an **SVG and PNG surfaces**.




Together they let us walk the display list that a PDF page contains and stream the final drawing instructions into memory - no temp files required.

### A minimal C API

The C++ core is wrapped in five plain-C entry points so any language with FFI can bind to it:
    
    
    /* pdf2svg.h - simplified */
    void* pdf_open_doc(const unsigned char* bytes, int len, int* out_page_count);
    void  pdf_close_doc(void* doc);
    
    unsigned char* pdf_get_page_data(
            void* doc, int page_num,
            bool force_to_png,          /* fallback switch           */
            int  dpi,                   /* raster DPI for PNG pages  */
            int* out_len,
            bool* out_is_svg            /* tells caller PNG vs SVG   */
    );
    
    void pdf_release_buffer(unsigned char* buffer);

Under the hood `pdf_get_page_data` looks at Poppler’s text mapping to decide whether the page is vector-friendly. If it’s an “image only” page (e.g., a scanned sheet), Cairo renders it onto a PNG surface at the requested DPI.

Implementation of the - `pdf_get_page_data`
    
    
    unsigned char*
    pdf_get_page_data(void*   doc_handle,
           int     page_num,
           bool    force_to_png,
           int     dpi,
           int*    out_len,
           bool*   out_is_svg)
    {
        auto* ctx = static_cast<PdfDoc*>(doc_handle);
        PopplerPage* page = poppler_document_get_page(ctx->doc, page_num);
        if (!page) {
            *out_len    = 0;
            *out_is_svg = false;
            return nullptr;
        }
    
        double w, h;
        poppler_page_get_size(page, &w, &h);
    
        bool has_text = false;
        bool image_only = false;
    
        if (!force_to_png) {
            char* txt = poppler_page_get_text(page);
            has_text = (txt && *txt != '\0');
            g_free(txt);
    
            GList* images = poppler_page_get_image_mapping(page);
            const double tol = 0.5;
    
            for (GList* iter = images; iter; iter = iter->next) {
                auto* m = static_cast<PopplerImageMapping*>(iter->data);
                if (fabs(m->area.x1) < tol &&
                    fabs(m->area.y1) < tol &&
                    fabs(m->area.x2 - w) < tol &&
                    fabs(m->area.y2 - h) < tol)
                {
                    image_only = true;
                    break;
                }
            }
            poppler_page_free_image_mapping(images);
        } else {
            image_only = true;
        }
    
        std::vector<unsigned char> buf;
        if (image_only && !has_text) {
            if (dpi <= 0)
                dpi = 72;
    
            double scale      = dpi / 72.0;
            int    width_px   = static_cast<int>(std::ceil(w * scale));
            int    height_px  = static_cast<int>(std::ceil(h * scale));
    
            // Rasterize to PNG
            cairo_surface_t* img_surf = cairo_image_surface_create(
                CAIRO_FORMAT_ARGB32,
                width_px,
                height_px);
    
            cairo_t* img_cr = cairo_create(img_surf);
    
            cairo_scale(img_cr, scale, scale);
    
            poppler_page_render(page, img_cr);
    
            cairo_destroy(img_cr);
    
            cairo_surface_write_to_png_stream(img_surf, write_cb, &buf);
    
            cairo_surface_destroy(img_surf);
    
            *out_is_svg = false;
        } else {
            // Emit SVG
            cairo_surface_t* svg_surf = cairo_svg_surface_create_for_stream(
                write_cb, &buf, w, h);
    
            cairo_t* svg_cr = cairo_create(svg_surf);
            poppler_page_render_for_printing(page, svg_cr);
    
            cairo_destroy(svg_cr);
            cairo_surface_destroy(svg_surf);
    
            *out_is_svg = true;
        }
    
        g_object_unref(page);
    
        *out_len = static_cast<int>(buf.size());
        if (*out_len == 0) {
            *out_len    = 0;
            *out_is_svg = false;
            return nullptr;
        }
    
        unsigned char* out = static_cast<unsigned char*>(std::malloc(buf.size()));
        if (!out) {
            *out_len    = 0;
            *out_is_svg = false;
            return nullptr;
        }
    
        std::memcpy(out, buf.data(), buf.size());
    
        return out;
    }

**Key decisions**

  * **Single marshalled buffer.** The native side allocates one contiguous block so any .NET caller - Mono, CoreCLR, AOT - can copy and free safely.

  * `ByteSink` is a trivial `std::vector<uint8_t>` wrapper

no libpng or gzip is pulled in - Cairo writes PNG/SVG bytes directly.

  * **Tolerance for "mixed" pages.** If _any_ vector/text survives, keep SVG

otherwise fall back to PNG. That rule kept our Word files tiny yet visually identical.




### Building the shared object / DLL

The repository is set up with **CMake + vcpkg** :
    
    
    git clone https://github.com/Forevka/pdf2svgwrapper
    cd pdf2svgwrapper
    git submodule update --init --recursive   # pulls vcpkg
    mkdir build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release
    cmake --build .

This produces `pdf2svgwrapper.dll` \+ bunch dependencies (Windows) or `libpdf2svgwrapper.so` (Linux).

## Shipping it to .NET

### P/Invoke bindings

Because the native API is pure C, the C# side is a handful of `[DllImport]` declarations:
    
    
    static class NativeMethods 
    {
      [DllImport("native-svg2pdf/pdf2svgwrapper", CallingConvention = CallingConvention.Cdecl)]
      public static extern IntPtr pdf_open_doc(
        IntPtr pdfData,
        int pdfLen,
        out int pageCount
      );
    
      [DllImport("native-svg2pdf/pdf2svgwrapper", CallingConvention = CallingConvention.Cdecl)]
      public static extern IntPtr pdf_get_page_data(
        IntPtr docHandle,
        int pageNum,
        bool isForcePng,
        int dpi,
        out int dataLen,
        out bool isSvg
      );
    
      [DllImport("native-svg2pdf/pdf2svgwrapper", CallingConvention = CallingConvention.Cdecl)]
      public static extern void pdf_close_doc(IntPtr docHandle);
    
      [DllImport("native-svg2pdf/pdf2svgwrapper", CallingConvention = CallingConvention.Cdecl)]
      public static extern void pdf_release_buffer(IntPtr ptr);
    }

A thin `Pdf2SvgInterop` class converts those raw pointers into managed `byte[]` or `MemoryStream`.

Explaining `Pdf2SvgInterop.ConvertPdfPages`
    
    
    public static IEnumerable<PdfPageData> ConvertPdfPages(byte[] pdfBytes, bool isForceToPng, int dpi = 300)
    {
        // pin the managed array
        var handle = GCHandle.Alloc(pdfBytes, GCHandleType.Pinned);
        try
        {
            IntPtr ptr = NativeMethods.pdf_open_doc(handle.AddrOfPinnedObject(), pdfBytes.Length, out int pageCount);
            if (ptr == IntPtr.Zero) 
                     throw new PopplerCairoConvertationException("Failed to open PDF.");
    
            try
            {
                for (int i = 0; i < pageCount; i++)
                {
                    IntPtr dataBuf = NativeMethods.pdf_get_page_data(ptr, i, isForceToPng, dpi, out int dataLen, out
                        var isSvg);
    
                    if (dataBuf == IntPtr.Zero) throw new PopplerCairoConvertationException($ "Page {i} conversion failed.");
    
                    try
                    {
                        var dataBytes = new byte[dataLen];
                        Marshal.Copy(dataBuf, dataBytes, 0, dataLen);
    
                        yield return new PdfPageData
                        {
                            Data = new MemoryStream(dataBytes, writable: false),
                            IsSvg = isSvg,
                        };
                    }
                    finally
                    {
                        NativeMethods.pdf_release_buffer(dataBuf);
                    }
                }
            }
            finally
            {
                NativeMethods.pdf_close_doc(ptr);
            }
        }
        finally
        {
            handle.Free();
        }
    }

### Why this shape?

Concern| How the method addresses it  
---|---  
**GC pinning**|  We never hand managed memory to C++; instead C++ allocates, C# copies.  
**Large PDFs**|  Because we use generators:  
Only one page’s bytes sit on the managed heap at any moment.  
`try/finally` in an iterator runs when the enumerator is disposed, so the native Poppler document cannot leak - even if the consumer breaks out of the `foreach`.  
**Thread safety**|  Each call operates on its own document handle - no global state.  
**AOT friendliness**|  Pure `[DllImport]`, no `Marshal.StructureToPtr`, so the IL linker keeps only what it needs on iOS/Android trims.  
**Back-pressure**|  The caller decides when to dispose or stream each `PageResult`; we don’t hold unmanaged buffers past the loop.  
  
No `SafeHandle` close-over a `try/finally` instead - this keeps allocations to a minimum in the hot loop.

**Cross-platform lookup** is handled by the NuGet’s `runtimes/*/native/` layout, so `pdf2svgwrapper` resolves to `pdf2svgwrapper.dll`, `.so`, or `.dylib` automatically.

## NuGet Access

This package can be added to your project via this command
    
    
    dotnet add package PDF2SVG.PopplerCairo.Bindings

That does three things automatically:

What happens|   
---|---  
**Managed DLL is referenced** (`PDF2SVG.PopplerCairo.Bindings.dll`)| Gives you the `Pdf2SvgInterop` class out of the box.  
**Native binaries are copied** to `runtimes/*/native/` in `obj`/`bin`| The correct `pdf2svgwrapper` (`.dll`, `.so`, or `.dylib`) lands beside your app at publish time - no extra MSBuild tweaks.  
`DllImport`**resolution just works** on Windows and Linux.| You can `dotnet publish -r win-x64` or`linux-x64`and run immediately.  
  
## Example of usage

The sample program shows basic usage:
    
    
    byte[] pdfBytes = File.ReadAllBytes("./input-2.pdf");
    
    var pageData = Pdf2SvgInterop.ConvertPdfPages(pdfBytes, true); // optional dpi can be provided
    
    var index = 0;
    foreach (var pdfPageData in pageData)
    {
        if (pdfPageData.IsSvg)
            File.WriteAllBytes($"./output-{index}.svg", pdfPageData.Data.ToArray());
        else
        {
            File.WriteAllBytes($"./output-{index}.png", pdfPageData.Data.ToArray());
        }
    
        Console.WriteLine($"Pdf page {index} processed");
        index++;
    }
    
    
    Console.WriteLine("Pdf processed");

This will read `input-2.pdf` from the project directory and create `output-{index}.svg` or `output-{index}.png` for each page.

## Where to Grab the Code

| Repository|   
---|---|---  
**Native C++ engine** \- Poppler + Cairo wrapper| [https://github.com/Forevka/pdf2svgwrapper](https://github.com/Forevka/pdf2svgwrapper)| CMake project, minimal C API, vcpkg manifests, ready to cross-compile Windows / Linux  
**.NET bindings & convenience helpers**| [https://github.com/Forevka/pdf2svg_poppler_cairo](https://github.com/Forevka/pdf2svg_poppler_cairo)| `PDF2SVG.PopplerCairo.Bindings` source, P/Invoke layer, sample console app  
**Published NuGet package**| [https://www.nuget.org/packages/PDF2SVG.PopplerCairo.Bindings](https://www.nuget.org/packages/PDF2SVG.PopplerCairo.Bindings/)| Pre-built managed DLL plus platform-specific native binaries  
**End-to-end demo**| `PDF2SVG.PopplerCairo.Use/Program.cs` file (inside the binding repo)| Opens a PDF, streams each page to SVG/PNG in-memory, and drops them into a disk  
  
## Conclusion

In under a week I went from "Word reports with blurry screenshots" to a **drop-in**`.NET`**helper that streams crisp SVG pages straight into Open XML**. The recipe was simple:

  1. Leverage **battle-tested C libraries** (Poppler + Cairo).

  2. Hide them behind a **five-function C facade**.

  3. Use **P/Invoke** to light them up in C#.

  4. Pack the native bits so downstream teams just reference a NuGet.




The result feels almost unfair: a few hundred lines of C++, a few dozen lines of C#, and suddenly every .NET app gets a PDF-to-SVG super-power.

So next time you bump into a "native only" library, remember - _bridging C/C++ to C# is usually the easy part._ The real magic is deciding **exactly the problem you want that native code to solve.**