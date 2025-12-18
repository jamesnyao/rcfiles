@echo off
setlocal enabledelayedexpansion

REM Prevent infinite recursion
if defined PYTHON3_WRAPPER_ACTIVE (
  py.exe %*
  exit /b %ERRORLEVEL%
)
set PYTHON3_WRAPPER_ACTIVE=1

set "FOUND="

REM Prefer .bat over .exe on Windows shims
for %%I in (python3.bat python3.exe) do (
  set "CAND=%%~$PATH:I"
  if defined CAND (
    REM Skip depot_tools at C:\dev\depot_tools\scripts
    if /I "!CAND:~0,26!"=="C:\dev\depot_tools\scripts" (
      set "CAND="
    )

    REM Skip Windows Store stubs
    if /I "!CAND:~0,51!"=="C:\Users\jamyao\AppData\Local\Microsoft\WindowsApps" (
      set "CAND="
    )

    REM Skip self
    if defined CAND if /I not "!CAND!"=="%~f0" (
      set "FOUND=!CAND!"
      goto :found_done
    )
  )
)

:found_done
echo DepoToolsShimCheck: FOUND="!FOUND!"

if defined FOUND (
  "!FOUND!" %*
  exit /b %ERRORLEVEL%
)

REM Fallback
py.exe %*
