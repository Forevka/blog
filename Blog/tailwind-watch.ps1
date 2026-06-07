# Run the Tailwind standalone CLI in watch mode for live CSS iteration.
# Use alongside `dotnet run` (Razor runtime compilation is enabled, so .cshtml edits hot-reload too).
# The CLI binary is downloaded automatically by `dotnet build` (EnsureTailwindCli target).
& "$PSScriptRoot\..\tools\tailwind\tailwindcss-windows-x64.exe" `
    -c "$PSScriptRoot\tailwind.config.js" `
    -i "$PSScriptRoot\Styles\input.css" `
    -o "$PSScriptRoot\wwwroot\css\app.css" `
    --watch
