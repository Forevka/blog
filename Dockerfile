# Stage 1: Build the application
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build

# Set the working directory inside the container
WORKDIR /src

# Copy the entire source code into the container
COPY . .

# Restore dependencies
RUN dotnet restore "Blog.sln"

# Build and publish the application
RUN dotnet publish "Blog/Blog.csproj" -c Release -o /app/publish

# Stage 2: Build the runtime image
FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS runtime

# Set the working directory
WORKDIR /app

EXPOSE 80
EXPOSE 443

ENV ASPNETCORE_HTTPS_PORT https://+:443
ENV ASPNETCORE_URLS http://+:80

# Copy the published output from the build stage
COPY --from=build /app/publish .

# Start the application
ENTRYPOINT ["dotnet", "Blog.dll"]