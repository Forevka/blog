using Umbraco.Cms.Core.Models.PublishedContent;
using Umbraco.Cms.Web.Common;

namespace Blog.Helper;

public static class GetPageByAliasExt
{
    public static IPublishedContent? GetPageByAlias(this UmbracoHelper helper, string alias)
    {
        return helper.ContentAtRoot().SelectMany(x => x.DescendantsOrSelf()).FirstOrDefault(
            x => x.ContentType.Alias.Equals(alias, StringComparison.InvariantCultureIgnoreCase)
        );
    }
}
