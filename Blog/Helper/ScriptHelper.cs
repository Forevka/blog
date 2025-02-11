using Microsoft.AspNetCore.Html;
using Microsoft.AspNetCore.Mvc.Rendering;

namespace Blog.Helper;

public static class ScriptHelper
{
    private const string ScriptsHeadKey = "RegisteredHeadScripts";
    private const string ScriptsEndKey = "RegisteredEndScripts";

    // Registers a script string
    public static void RegisterScriptHead(this IHtmlHelper htmlHelper, string script)
    {
        var scripts = htmlHelper.ViewContext.HttpContext.Items[ScriptsHeadKey] as List<string>;
        if (scripts == null)
        {
            scripts = new List<string>();
            htmlHelper.ViewContext.HttpContext.Items[ScriptsHeadKey] = scripts;
        }
        scripts.Add(script);
    }

    // Renders all registered scripts as a single HTML string
    public static IHtmlContent RenderRegisteredScriptsHead(this IHtmlHelper htmlHelper)
    {
        var scripts = htmlHelper.ViewContext.HttpContext.Items[ScriptsHeadKey] as List<string>;
        if (scripts == null || scripts.Count == 0)
        {
            return HtmlString.Empty;
        }
        var combined = string.Join(Environment.NewLine, scripts);
        return new HtmlString(combined);
    }


    // Registers a script string
    public static void RegisterScriptEnd(this IHtmlHelper htmlHelper, string script)
    {
        var scripts = htmlHelper.ViewContext.HttpContext.Items[ScriptsEndKey] as List<string>;
        if (scripts == null)
        {
            scripts = new List<string>();
            htmlHelper.ViewContext.HttpContext.Items[ScriptsHeadKey] = scripts;
        }
        scripts.Add(script);
    }

    // Renders all registered scripts as a single HTML string
    public static IHtmlContent RenderRegisteredScriptsEnd(this IHtmlHelper htmlHelper)
    {
        var scripts = htmlHelper.ViewContext.HttpContext.Items[ScriptsEndKey] as List<string>;
        if (scripts == null || scripts.Count == 0)
        {
            return HtmlString.Empty;
        }
        var combined = string.Join(Environment.NewLine, scripts);
        return new HtmlString(combined);
    }
}