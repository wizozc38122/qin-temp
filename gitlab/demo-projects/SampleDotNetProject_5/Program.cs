using System;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Hosting;

namespace SampleDotNetProject
{
    public class Program
    {
        public static void Main(string[] args)
        {
            // --- 下面這段刻意保留不良的程式碼習慣，這樣你的 SonarQube 才會有發報 ---
            int unusedVariable = 42; 
            
            try 
            {
                DoSomething();
            } 
            catch (Exception ex) 
            {
                // Empty catch block
            }

            CreateHostBuilder(args).Build().Run();
        }

        public static IHostBuilder CreateHostBuilder(string[] args) =>
            Host.CreateDefaultBuilder(args)
                .ConfigureWebHostDefaults(webBuilder =>
                {
                    webBuilder.Configure(app =>
                    {
                        app.UseRouting();

                        app.UseEndpoints(endpoints =>
                        {
                            endpoints.MapGet("/", async context =>
                            {
                                await context.Response.WriteAsync("🚀 Hello World! 成功了！此為由純淨 ci-image 打包，並透過極小化 aspnet 映像檔執行的 Web 網站！");
                            });
                        });
                    });
                });

        static void DoSomething() 
        {
            // Hardcoded password example 
            string password = "super_secret_password_123";
            Console.WriteLine("Doing something internally...");
        }

        // Unused method
        public void NeverCalledMethod() 
        {
            Console.WriteLine("This is never executed.");
        }
    }
}
