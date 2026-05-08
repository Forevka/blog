# forevka.dev — full blog dump

Total posts recovered: 3

================================================================================

# Crafting a Result Pattern in C#: A Comprehensive Guide

> Source: https://forevka.dev/articles/crafting-a-result-pattern-in-c-a-comprehensive-guide/

---

# Crafting a Result Pattern in C#: A Comprehensive Guide

This article gathers best practices and insights from various implementations of the result pattern—spanning multiple languages and frameworks—to help you integrate these ideas seamlessly into your .NET applications.

### Introduction to Result Pattern vs. Exception-Based Flow

Traditionally, C# applications have relied on exceptions for error handling. While exceptions are invaluable for truly unexpected issues, they can be overused for expected or recoverable failures, leading to several issues:

  * **Performance Improvements:**  
Throwing and catching exceptions is inherently expensive. The result pattern avoids this overhead by returning a structured value, which is especially beneficial in high-volume applications.

  * **Simplified Code Flow:**  
With the result pattern, success and failure cases are explicitly represented. Developers don’t need to sift through try/catch blocks—the control flow is clearly delineated.

  * **Maintainability:**  
Centralizing error handling in a result type makes your code easier to maintain. When error logic is encapsulated within a well-defined type, debugging and testing become less complex.

  * **Clarity in Intent:**  
When a function returns a result, it’s immediately clear to the consumer that the operation may fail. This explicit contract improves code readability and encourages handling both outcomes.




The Cultural Relevance of the Result Pattern

> Every good programmer has likely reinvented the result pattern at least once in their life to control flow, and even languages like Go have embedded it as a core feature. This idea isn’t unique to .NET - it’s a recurring theme throughout programming history.
> 
> Back in the day, C programmers would often return error codes from functions (say hello to the application exit codes), leaving it to the caller to inspect and handle each outcome. It wasn’t elegant, but it was a solution born of necessity. As programming languages evolved, exceptions emerged in languages like C++ and Java. They promised a cleaner way to handle errors by separating normal logic from error logic. Yet, as many of us have discovered, exceptions can be heavy, unpredictable, and hard to manage in high-performance or highly scalable systems. Microsoft itself strongly recommends against using exception-based control flow: [First](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/exception-throwing "Design Guidelines"), [Second](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/best-practices?view=aspnetcore-9.0#minimize-exceptions "Best Practice"), [Third](https://learn.microsoft.com/en-us/dotnet/standard/exceptions/ "Exceptions vs Traditional way") and even [Fourth](https://learn.microsoft.com/en-us/dotnet/standard/exceptions/best-practices-for-exceptions ".NET standart best practice") mention.
> 
> About the result pattern. Functional languages like Haskell embraced a similar concept with the “Either” type, a tool designed to express success or failure in a single, unified return value. This idea found fertile ground in languages like F#, where a built-in Result type made error handling both explicit and type-safe. Fast forward to modern times, and Rust has taken the concept to a new level with its own Result<T, E> type, ensuring that error handling is not an afterthought but a core part of the function’s contract.
> 
> Even in the dynamic world of JavaScript and later in TypeScript (child of MS), developers have created patterns and libraries that mimic this approach, favoring explicit control flow over hidden exception paths. What’s fascinating is that while the syntax and language paradigms have changed over the decades, the core challenge of cleanly and predictably handling errors remains the same.

### Comparing Existing Libraries in the .NET Ecosystem

The main point of this article is to help implement own Result/Exception/Error that fits your project needs, but first of all let's compare what community can offer.

Several libraries implement variations of the result pattern, each with its own strengths and trade-offs:

  * [**OneOf**](https://github.com/mcintyre321/OneOf "OneOf"):

    * _Benefits:_  
Provides a clean way to create discriminated unions in C#. It integrates well with pattern matching and allows you to return one of multiple types.

    * _Limitations:_  
It may require additional boilerplate or careful handling when converting between types. **We are going to use this library as a base for our result pattern.**

  * [**CSharpFunctionalExtensions**](https://github.com/vkhorikov/CSharpFunctionalExtensions "CSharpFunctionalExtensions"):

    * _Benefits:_  
Offers a rich set of functional constructs, including Result, Value Objects, and even support for lazy evaluation.

    * _Scenarios:_  
This library might be better suited for projects where you want a full suite of functional programming tools alongside the result pattern.

  * [**Either**](https://github.com/louthy/csharp-monad "Either"):

    * _Benefits:_  
Similar to OneOf, Either provides a way to encapsulate success or failure without exceptions.

    * _Scenarios:_  
Use this when you want a simpler, more lightweight implementation.




Each library has its merits. Choosing one depends on your project’s complexity, the team’s familiarity with functional patterns, and specific requirements regarding type safety and boilerplate reduction.

* * *

### Step-by-Step Implementation of a Custom Result Pattern

Basic Setup and Structure

Start by defining a result type that encapsulates both success and error cases. This is a core of our pattern, that will be used across all project. I strongly recommend to move this code to separate .csproj for easier dependency management.

Defining the Interfaces and Result Types
    
    
    /// <summary>
    /// In C#, pattern matching against generic types requires a known type argument at compile time.
    /// Since IResultPattern(T) is generic and the type parameter T is unknown, direct pattern matching is not possible.
    /// To overcome this, a non-generic base interface (IResultPattern) provides a common contract,
    /// enabling type-agnostic operations without resorting to reflection, which can impact performance and maintainability.
    /// see <see cref="ResultActionFilter"/>
    /// </summary>
    public interface IResultPattern
    {
        bool IsSuccess { get; }
        bool IsProblem { get; }
        object Success { get; }
        Problem Problem { get; }
    }
    
    public interface IResultPattern<out T> : IResultPattern
    {
        new T Success { get; }
    }
    
    [GenerateOneOf]
    public partial class Result<T> : OneOfBase<T, Problem>, IResultPattern<T> where T : class
    {
        public bool IsSuccess => IsT0;
        public bool IsProblem => IsT1;
    
        public T Success => AsT0;
        public Problem Problem => AsT1;
    
        // Explicit implementation for non-generic interface
        object IResultPattern.Success => Success;
    }
    
    [GenerateOneOf]
    public partial class VoidResult : OneOfBase<bool, Problem>, IResultPattern<bool>
    {
        public bool IsSuccess => IsT0 && AsT0;
        public bool IsProblem => IsT1;
    
        public bool Success => AsT0;
        public Problem Problem => AsT1;
    
        // Explicit implementation for non-generic interface
        object IResultPattern.Success => Success;
    }

Defining the Error (Problem) Type
    
    
    public class Problem
    {
        [JsonIgnore]
        public HttpStatusCode StatusCode { get; init; }
    
        [JsonPropertyName("Description")]
        public string? Description { get; init; }
    
        [JsonPropertyName("ErrorCode")]
        public ErrorCode ErrorCode { get; init; }
    
        [JsonPropertyName("Errors")]
        public List<BusinessLogicCase> Errors { get; set; } = new();
    
        public override string ToString()
        {
            return JsonSerializer.Serialize(this);
        }
    }

The design starts with the IResultPattern interfaces.   
The non-generic IResultPattern defines a simple contract. It tells if an operation succeeded or failed and exposes either a success value or error details. The generic IResultPattern<T> builds on this. It replaces the untyped success property with a strongly typed version. This makes later code more type safe without losing flexibility.

Next is the Result<T> class. It uses the OneOf library to hold either a value of type T or a Problem.   
It provides clear properties to check if the result is a success or a problem. The [GenerateOneOf] attribute cuts down on boilerplate by generating necessary conversion methods. This class is the **backbone of the result pattern**.

VoidResult follows a similar approach.   
It is used when no data needs to be returned. It wraps a boolean value and a Problem. A true boolean indicates a successful operation. It standardizes how void operations are handled in this pattern.

On the other hand the Problem class encapsulates error information.  
It holds a status code, a description, an error code, and a list of detailed errors. It replaces the need for exceptions by providing a structured error response. Its JSON serialization helps with logging and API responses. We intend to return this object as the result of the API in case of an error.

Together, these components create a system that clearly separates success from failure. They provide a consistent way to handle outcomes throughout the application.

* * *

At this point you are ready to go, implementation are ready to use. But I continue to add some features that are especially developed to be used in [ASP.NET](http://asp.net/) Core, such as OpenAPI specification generation and proper handling of direct return of the Result object from the API route.  
But first, let's dig down what benefits do we have with OneOf library

### Integrating the OneOf Library

By leveraging the OneOf library, we create a discriminated union that cleanly represents either a success (with a value) or a problem (with error details). This design simplifies the handling of multiple possible states and keeps your domain logic clean.

The GenerateOneOf attribute is a real game-changer. It automatically creates conversion methods that let you work with your result type almost as if it were a union of two unrelated types. Behind the scenes, it generates a constructor that wraps a union containing either a success value or an error. This means you can build a Result<T> without worrying about a common base class for T and Problem.

Generated code that allow us to do "magic" with types:
    
    
    partial class Result<T>
    {
        public Result(OneOf.OneOf<T, global::AppraiSys.Essential.ResultPattern.ResultPattern.Problem> _) : base(_) { }
    
        public static implicit operator Result<T>(T _) => new Result<T>(_);
        public static explicit operator T(Result<T> _) => _.AsT0;
    
        public static implicit operator Result<T>(global::AppraiSys.Essential.ResultPattern.ResultPattern.Problem _) => new Result<T>(_);
        public static explicit operator global::AppraiSys.Essential.ResultPattern.ResultPattern.Problem(Result<T> _) => _.AsT1;
    }

For example, notice the implicit conversion from T to Result<T>. This lets you simply return a value of type T from a method, and the compiler wraps it for you. Likewise, if you return a Problem, it gets wrapped automatically. There’s also an explicit conversion back from Result<T> to T or to Problem. These methods allow you to extract the underlying value when you need it.

Imagine you have a method that can either produce a valid model or an error. With the generated conversions, your method looks clean:
    
    
    public async Task<Result<ModelDto>> DoSomething()
    {
        if (/* some error condition */)
            return new Problem { /* error details */ };
    
        return new ModelDto { /* model data */ };
    }

Here, you don’t need to wrap ModelDto or Problem in a special base class. The generated methods handle that. You can return either type directly. This provides you with powerful flexibility. It means your API can express multiple outcomes in a natural way. The code remains concise, and the intent stays clear.

In short, the GenerateOneOf attribute drills down to the core of result handling. It removes boilerplate code and lets you focus on the business logic. With these conversion operators in place, your methods can effortlessly return different types while maintaining type safety and clarity.

* * *

### Result object and API

Now you may ask a question, what if we directly return a Result object from API route? What outcome will we have?  
Well, we need to think about it and create such integration to generate clear OpenAPI specification without mention of the Result and a proper handling for cases when our Result is not success at all but Problem returned by underlying logic. 

Let's start with simpler and update OpenAPI spec generation for all routes that returns Result<T>, to make this happen let's create OpenApiResultOperationFilter.  
The OpenApiResultOperationFilter is our bridge to clear and accurate API documentation. Imagine you have an API method that returns our custom Result type. Without this filter, Swagger or other OpenAPI tools might simply see an ambiguous object. They wouldn’t know if your method returns a ModelDto on success or a Problem on error. The generated docs would be vague, leaving consumers uncertain about the actual data structure.

With the filter in place, the logic drills down into the method’s return type. It starts by unwrapping any Task<> (I hope that all your routes are async, if not Houston we have a problem) wrappers to reveal the underlying type. Then it checks if this type implements IResultPattern. This is where our non-generic IResultPattern interface comes into play. It allows a **type-agnostic check so that regardless of the specific success type** , the filter recognizes the pattern.

Once confirmed, the filter clears the default responses and builds a clear specification. It generates a schema based on the success type if there is one. For instance, if your method returns a Result<ModelDto>, the filter uses reflection to generate a schema for ModelDto. It also sets up distinct responses for different HTTP status codes. A 200 response might indicate success with a ModelDto payload, while responses like 400 or 401 point to a Problem schema. Even a 500 response is handled, providing a schema for ProblemDetails.
    
    
    public class OpenApiResultOperationFilter : IOperationFilter
    {
        public void Apply(OpenApiOperation operation, OperationFilterContext context)
        {
            // Get the return type of the method (e.g., Task<Result<,>>)
            var returnType = context.MethodInfo.ReturnType;
    
            // Unwrap Task<>
            if (returnType.IsGenericType && returnType.GetGenericTypeDefinition() == typeof(Task<>))
            {
                returnType = returnType.GetGenericArguments()[0];
            }
    
            // Check if returnType implements IResultPattern
            if (!typeof(IResultPattern).IsAssignableFrom(returnType))
            {
                return;
            }
    
            var genericArgument = returnType.GetGenericArguments().FirstOrDefault();
            operation.Responses.Clear();
    
            var isVoidResult = genericArgument == null;
    
            var schema = isVoidResult ? null : context.SchemaGenerator.GenerateSchema(genericArgument, context.SchemaRepository);
    
            var isGenericIList = genericArgument?.GetInterfaces()
                .Any(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IList<>)) ?? false;
    
            operation.Responses["200"] = new OpenApiResponse
            {
                Description = isVoidResult ? "Ok" : isGenericIList ? $"Ok, array of {genericArgument!.GetGenericArguments()[0].Name}" : $"Ok, {genericArgument!.Name}",
                Content = new Dictionary<string, OpenApiMediaType>
                {
                    ["application/json"] = new()
                    {
                        Schema = schema,
                    },
                },
            };
    
            operation.Responses["204"] = new OpenApiResponse
            {
                Description = "No content",
            };
    
            var notSuccessResultSchema = context.SchemaGenerator.GenerateSchema(typeof(Problem), context.SchemaRepository);
    
            operation.Responses["400"] = new OpenApiResponse
            {
                Description = "Bad request, validation error",
                Content = new Dictionary<string, OpenApiMediaType>
                {
                    ["application/json"] = new()
                    {
                        Schema = notSuccessResultSchema,
                    },
                },
            };
    
            operation.Responses["401"] = new OpenApiResponse
            {
                Description = "Not Authorized",
                Content = new Dictionary<string, OpenApiMediaType>
                {
                    ["application/json"] = new()
                    {
                        Schema = notSuccessResultSchema,
                    },
                },
            };
    
            var internalServerErrorSchema = context.SchemaGenerator.GenerateSchema(typeof(ProblemDetails), context.SchemaRepository); 
    
            operation.Responses["500"] = new OpenApiResponse
            {
                Description = "Server side error",
                Content = new Dictionary<string, OpenApiMediaType>
                {
                    ["application/json"] = new()
                    {
                        Schema = internalServerErrorSchema,
                    },
                },
            };
        }
    }

This logic ensures that every potential outcome of your API method is documented. If you return a Problem, clients see a well-defined error structure. If you return a successful result, they know exactly what to expect. Without this filter, your API documentation would lack this level of detail. Consumers might have to guess or read through code, instead of relying on an automatically generated, clear contract.

In essence, the OpenApiResultOperationFilter elevates your API documentation. It translates our custom result pattern into a format that tools like Swagger can display, ensuring that both success and error responses are accurately represented. This makes your API more transparent and easier to integrate with, benefiting both developers and end users.

So, for code like:
    
    
    [HttpGet]
    [Permission(ResourceConstant.User, ActionsConstant.Read)]
    public async Task<Result<List<UserClientViewModel>>> GetClientsList()
    {
        return await _userService.GetClientList(); // note, this method directly return Result<List<UserClientViewModel>>
    }

Swagger spec will look like:

![](/web/20250326135332im_/https://forevka.dev/media/lvqji5cn/result-open-api-spec.png)

Proper generated body for all possible return types

### Unified API Response Handling with ResultActionFilter

The ResultActionFilter is our way of centralizing response transformation. It intercepts every action result and checks if it implements the IResultPattern interface. Thanks to this, we don't have to clutter our controller actions with repetitive if-checks and manual response creation. When an action returns a result, the filter first waits for the action to complete. It then examines the result. If the result is an object that follows our custom pattern, the filter inspects whether it represents success or a problem.

If the result signals success, the filter checks further. In cases where the success value is a boolean, it translates a true value into an HTTP 200 OK response and a false into a 400 Bad Request. Otherwise, it wraps the success value in an HTTP 200 OK response. In the event of a problem, the filter extracts the error details and creates a response using the provided HTTP status code from the error object.
    
    
    public class ResultActionFilter : IAsyncActionFilter
    {
        public async Task OnActionExecutionAsync(ActionExecutingContext context, ActionExecutionDelegate next)
        {
            var resultContext = await next();
    
            if (resultContext.Result is ObjectResult { Value: IResultPattern resultPatternValue })
            {
                if (resultPatternValue.IsSuccess)
                    if (resultPatternValue.Success is bool voidResult)
                        resultContext.Result = voidResult ? new OkResult() : new BadRequestResult();
                    else
                        resultContext.Result = new OkObjectResult(resultPatternValue.Success);
                else
                {
                    var errorResult = resultPatternValue.Problem;
    
                    resultContext.Result = new ObjectResult(errorResult)
                    {
                        StatusCode = (int)errorResult!.StatusCode,
                    };
                }
            }
        }
    }
    
    
    public class ResultActionFilterProvider : IFilterProvider
    {
        public void OnProvidersExecuting(FilterProviderContext context)
        {
            var filter = new ResultActionFilter();
    
            var filterItem = new FilterItem(new FilterDescriptor(filter, FilterScope.Action))
            {
                Filter = filter,
                IsReusable = false,
            };
    
            context.Results.Add(filterItem);
        }
    
        public void OnProvidersExecuted(FilterProviderContext context) { }
    
        public int Order => -1000;
    }

Note: this filter intended to be used as a GlobalFilter i.e. on all routes.

Without this filter, each controller action would need to handle this branching logic individually. That would lead to duplicate code scattered throughout the project and increased chances of inconsistencies. The filter makes the process seamless. The ResultActionFilterProvider ensures that this filter is automatically registered. It attaches the filter to every action without the developer needing to manually add attributes to each controller.

In short, the ResultActionFilter simplifies our API responses. It guarantees that the custom result pattern is consistently transformed into appropriate HTTP responses. This not only cleans up our code but also improves the overall maintainability of the application.

### Comparing Result Pattern to Exception Flow

When you compare the result pattern to the traditional exception approach, the difference becomes clear in how the flow is controlled. Imagine a method that fetches a user by ID. With the result pattern, the method simply returns a result that holds either the user or a problem. There’s no need for try/catch blocks. The code directly checks if the user exists and returns the appropriate result. For example:
    
    
    public Result<User> GetUserById(int id)
    {
        var user = repository.FindUser(id);
        if (user is null)
            return new Problem { StatusCode = HttpStatusCode.NotFound, Description = "User not found" };
        return user;
    }

In a traditional exception-based flow, the same method throws an exception when the user isn’t found. This interrupts the normal flow and requires handling the exception somewhere up the call chain:
    
    
    public User GetUserById(int id)
    {
        var user = repository.FindUser(id);
        if (user is null)
            throw new NotFoundException("User not found");
        return user;
    }

The result pattern keeps the code flow linear and clear. The consumer of the method just examines the result instead of dealing with an exception.

Now consider a scenario where an operation might have multiple outcomes, such as processing a payment. With the result pattern, you can handle different cases—like validation errors, warnings, or success—by returning a structured result:
    
    
    public Result<Payment> ProcessPayment(PaymentRequest request)
    {
        if (!Validate(request))
            return new Problem { StatusCode = HttpStatusCode.BadRequest, Description = "Validation error" };
    
        var payment = paymentService.Process(request);
        if (payment.IsProblem)
        {
            logger.LogWarning("payment processing went wrong {Problem}", payment.Problem);
            return new WarningPayment(payment, "Payment processed with warnings"); // you can derive from Problem type if you want to
        }
        
        return payment; //or payment.Success
    }

Contrast this with the traditional approach where you use try/catch blocks and throw different exceptions for each outcome:
    
    
    public Payment ProcessPayment(PaymentRequest request)
    {
        try
        {
            if (!Validate(request))
                throw new ValidationException("Validation error");
    
            var payment = paymentService.Process(request);
            if (payment.IsWarning)
                throw new PaymentWarningException("Payment processed with warnings");
    
            return payment;
        }
        catch (Exception ex)
        {
            // Handle or log exception
            throw;
        }
    }

Using the result pattern creates a more predictable and clean flow. There’s no scattering of try/catch blocks throughout the code. Instead, each method clearly communicates its possible outcomes by returning a well-defined result. Consumers can then simply check if the operation was successful or if there was a problem, without digging through exception handling logic. This leads to code that is easier to maintain and test, and overall makes the developer’s life a bit simpler.

* * *

### Benchmarking the Result Pattern

Using BenchmarkDotNet, the following code demonstrates the performance benefits of the result pattern compared to exception throwing:
    
    
    [MemoryDiagnoser]
    public class ResultPatternBenchmark
    {
        private const int Iterations = 100_000;
    
        private Result<string> GetResultPatternResult()
        {
            if (new Random().Next(0, 2) == 0)
                return "Success";
    
            return new Problem();
        }
    
        private int ThrowException()
        {
            if (new Random().Next(0, 2) == 0)
                return 42;
    
            throw new InvalidOperationException("An error occurred");
        }
    
        [Benchmark]
        public void BenchmarkResultPattern()
        {
            for (int i = 0; i < Iterations; i++)
            {
                var result = GetResultPatternResult();
                // Optionally, do something with the result
            }
        }
    
        [Benchmark]
        public void BenchmarkExceptionThrowing()
        {
            for (int i = 0; i < Iterations; i++)
            {
                try
                {
                    var value = ThrowException();
                    // Optionally, do something with the value
                }
                catch (Exception)
                {
                    // Optionally, handle the exception
                }
            }
        }
    }
    
    
    internal class Program
    {
        static void Main(string[] args)
        {
            BenchmarkRunner.Run<ResultPatternBenchmark>();
        }
    }

Benchmark Results:
    
    
    BenchmarkDotNet v0.14.0, Windows 10 (10.0.19045.5487/22H2/2022Update)
    11th Gen Intel Core i7-11700K 3.60GHz, 1 CPU, 16 logical and 8 physical cores
    .NET SDK 9.0.101
      [Host]     : .NET 8.0.11 (8.0.1124.51707), X64 RyuJIT AVX-512F+CD+BW+DQ+VL+VBMI [AttachedDebugger]
      DefaultJob : .NET 8.0.11 (8.0.1124.51707), X64 RyuJIT AVX-512F+CD+BW+DQ+VL+VBMI
    
    | Method                     | Mean       | Error     | StdDev    | Gen0      | Allocated |
    |--------------------------- |-----------:|----------:|----------:|----------:|----------:|
    | BenchmarkResultPattern     |   9.241 ms | 0.1739 ms | 0.4132 ms | 1765.6250 |  14.12 MB |
    | BenchmarkExceptionThrowing | 185.322 ms | 1.6657 ms | 1.3910 ms | 2000.0000 |  17.55 MB |
    

The result pattern method completes in just a few milliseconds and uses significantly less memory, while the exception method takes over 185 milliseconds with much higher memory allocation. This benchmark drives home the point that by avoiding exceptions for routine control flow, we can achieve much better performance, especially in high-volume scenarios.

* * *

### Conclusion

In conclusion, adopting the result pattern transforms how our applications handle outcomes. It streamlines the code by making both success and error cases explicit, thereby eliminating the clutter of try/catch blocks. This clarity makes the code easier to maintain and test. Moreover, the centralized error management that the result pattern offers means that error handling is consistent across the application. As we have seen, the performance benefits are significant, reducing both execution time and memory overhead. In essence, the result pattern not only improves performance but also enhances the overall development experience, I believe it must be an essential tool in every programmer’s toolkit.

================================================================================

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

================================================================================

# Discriminated Unions & Result Pattern

> Source: https://forevka.dev/articles/discriminated-unions-result-pattern-part-1/

---

# What Are Discriminated Unions and how it related to maintainable code 

Have you ever wondered how you can make your code both robust and beautiful? In the realm of functional programming, discriminated unions (also known as algebraic data types) offer a powerful way to represent data with clarity and precision. 

### What Are Discriminated Unions? 

Imagine you’re an artist with a **perfectly organized palette**. Each color is distinct, and you know exactly when and how to use it. Discriminated unions work similarly—they allow you to define a type that can be one of several distinct variants. Each variant can carry its own specific data, making the whole construct a clear, self-documenting model of your domain.

### A Simple Pseudocode Example: 

The Option Type Consider a common scenario: you want to represent a value that might or might not be present. In many languages, this is done using a nullable type, but discriminated unions take a more explicit approach:
    
    
    type Option<T> =
        | Some(value: T)
        | None

Isn’t it refreshing to know that an `Option` is always either `Some` value or `None `— there’s no room for ambiguity?

### A Philosophical Detour: Mathematics, Art, and Code

Let’s take a moment to appreciate the deeper roots of discriminated unions. In mathematics, there is the concept of a _disjoint union_ —a way of combining sets so that each element’s origin is preserved. This idea is as old as mathematics itself, reflecting a timeless desire for clarity and order.

**Programming, at its best, is much like art or philosophy**. Every time you choose a design pattern or a type system, you’re making a statement about how you wish to interact with the world. By opting for discriminated unions, you’re saying, “I value explicitness, safety, and elegance.” Isn’t it inspiring to think that your code can be a canvas where logic meets creativity?

* * *

### Pattern Matching: The Heartbeat of Functional Programming

Once you’ve defined a discriminated union, the next step is to work with it. Enter **pattern matching**. This is the functional programmer’s secret weapon: a way to deconstruct and handle each variant explicitly.

### A Pseudocode Example: Handling an Option
    
    
    function process(option: Option<T>) {
        match option {
            case Some(value):
                print("Found a value: " + value)
            case None:
                print("No value found.")
        }
    }

Ask yourself: wouldn’t it be comforting to know that every possible case is handled? That’s the promise of pattern matching—it forces you to consider all outcomes, leaving no room for forgotten edge cases.

### The Benefits: Clarity, Safety, and Joy

1\. Expressiveness and Self-Documentation

When you define a type with a discriminated union, you lay out all possible states right before your eyes. No hidden surprises. Every variant is explicitly named, making your code not only easier to understand but also easier to maintain.

2\. Exhaustive Checking

Languages that support discriminated unions often come with compilers that check for exhaustive handling. This means if you add a new variant, your compiler will cheerfully (or sometimes sternly) remind you to handle it everywhere. Can you imagine the relief of knowing that your compiler is looking out for you?

3\. Eliminating Null-Related Bugs

By modeling optional values with a type like `Option`, you force yourself to handle both the presence and absence of data explicitly. This approach virtually eliminates those annoying null pointer exceptions. Isn’t it time we said goodbye to those runtime gremlins?

* * *

### Discriminated Unions vs. Object-Oriented Polymorphism

In object-oriented programming, you might use polymorphism and inheritance to achieve similar behavior. However, discriminated unions offer a more straightforward and less error-prone alternative. Instead of navigating complex inheritance trees, you declare every possibility upfront.

A Pseudocode Example: Modeling Errors

Consider a system that can encounter different kinds of errors:
    
    
    type Error =
        | NotFound(message: String)
        | PermissionDenied(message: String)

Every time you handle an `Error`, you must account for both possibilities. There’s no chance for an unhandled error type to slip through the cracks.

* * *

_Are you ready to let your code reflect the precision of a mathematician and the creativity of an artist?_

We will continue journey with the unions in the next chapter of series

================================================================================

