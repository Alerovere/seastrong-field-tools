@echo off
REM Double-click launcher for Windows: sets up (first run only) and starts
REM the Echosounder Bathymetry tool in a dedicated conda environment, then
REM opens it in your browser. See README.md for details.
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "ENV_NAME=seastrong-echosounder"
set "CONDA_ROOT="

where conda >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%i in ('conda info --base') do set "CONDA_ROOT=%%i"
) else (
    for %%D in (
        "%USERPROFILE%\anaconda3"
        "%USERPROFILE%\miniconda3"
        "%USERPROFILE%\miniforge3"
        "%ProgramData%\Anaconda3"
        "%ProgramData%\miniconda3"
        "%LOCALAPPDATA%\Continuum\anaconda3"
    ) do (
        if exist "%%~D\Scripts\activate.bat" (
            set "CONDA_ROOT=%%~D"
            goto :found_conda
        )
    )
)
:found_conda

if "%CONDA_ROOT%"=="" (
    echo.
    echo Could not find an Anaconda/Miniconda installation.
    echo Install Anaconda from https://www.anaconda.com/download, then try again.
    echo If you just installed it, try running this from an "Anaconda Prompt"
    echo instead of double-clicking, or reinstall with "Add Anaconda to my
    echo PATH" checked.
    echo.
    pause
    exit /b 1
)

call "%CONDA_ROOT%\Scripts\activate.bat" "%CONDA_ROOT%"

conda env list | findstr /B /C:"%ENV_NAME% " >nul
if errorlevel 1 (
    echo.
    echo First run -- creating the '%ENV_NAME%' conda environment.
    echo This installs Streamlit, pyTMD, and the other packages this tool
    echo needs, without touching your other conda environments. It can take
    echo a few minutes; later runs skip straight to launching the app.
    echo.
    call conda create -y -n "%ENV_NAME%" python=3.11
)

call conda activate "%ENV_NAME%"

echo Checking dependencies are up to date...
call pip install -q -r requirements.txt

echo.
echo Starting the app -- your browser should open automatically.
echo To stop it, close this window or press Ctrl+C.
echo.
call streamlit run app.py

pause
