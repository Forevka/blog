using Microsoft.AspNetCore.HttpOverrides;
using Umbraco.Cms.Web.Common.PublishedModels;
using Umbraco.Community.BlockPreview.Extensions;

WebApplicationBuilder builder = WebApplication.CreateBuilder(args);

builder.CreateUmbracoBuilder()
    .AddBackOffice()
    .AddWebsite()
    .AddComposers()
    .AddBlockPreview(options =>
    {
        options.BlockGrid = new()
        {
            Enabled = true,
            ContentTypes = [RichTextContent.ModelTypeAlias, ImageContent.ModelTypeAlias, CodeBlockContent.ModelTypeAlias],
            ViewLocations = ["/Views/Shared/ArticleComponents/{0}.cshtml"],
            Stylesheet = "/css/site.css",
        };

        options.BlockList = new()
        {
            Enabled = false,
        };
    })
    .Build();

// Configure Forwarded Headers Options
builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
});

WebApplication app = builder.Build();

await app.BootUmbracoAsync();


app.UseUmbraco()
    .WithMiddleware(u =>
    {
        u.UseBackOffice();
        u.UseWebsite();
    })
    .WithEndpoints(u =>
    {
        u.UseBackOfficeEndpoints();
        u.UseWebsiteEndpoints();
    });

await app.RunAsync();
