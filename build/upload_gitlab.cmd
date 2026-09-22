@echo off
setlocal
echo Oracle Quiz Platform - GitLab upload
echo This launcher uses HTTP on the configured school server.
echo Files and the token are not encrypted. Use a short-lived token.
echo.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish_gitlab.ps1" -SourceDirectory "%~dp0." -AllowHttp %*
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo Upload failed. Read the error above. Exit code: %RESULT%
if "%RESULT%"=="0" echo Finished. Read the result above; cancelled or dry runs do not upload files.
echo Do not share your access token when sending an error report.
pause
exit /b %RESULT%
