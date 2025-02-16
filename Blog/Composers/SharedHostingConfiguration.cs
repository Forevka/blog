using Microsoft.AspNetCore.DataProtection.AuthenticatedEncryption.ConfigurationModel;
using Microsoft.AspNetCore.DataProtection.AuthenticatedEncryption;
using Microsoft.AspNetCore.DataProtection;
using Umbraco.Cms.Core.Composing;

namespace Blog.Composers;

/// <summary>
/// this would be loaded via assembly exploration feature
/// </summary>
public class SharedHostingConfiguration : IComposer
{
    public void Compose(IUmbracoBuilder builder)
    {
        var path = "/keys";
        builder.Services
            .AddDataProtection()
            .PersistKeysToFileSystem(new DirectoryInfo(path))
            .UseCryptographicAlgorithms(new AuthenticatedEncryptorConfiguration
            {
                EncryptionAlgorithm = EncryptionAlgorithm.AES_256_CBC,
                ValidationAlgorithm = ValidationAlgorithm.HMACSHA256,
            });
    }
}