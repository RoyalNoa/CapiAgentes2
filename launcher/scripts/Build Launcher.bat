@echo off

setlocal EnableExtensions



for %%I in ("%~dp0..") do set "ROOT_DIR=%%~fI"

set "PROJECT_ROOT=%ROOT_DIR%\.."

set "SPEC_DIR=%ROOT_DIR%\pyinstaller"

set "SPEC=CapiAgentes_Docker_Manager.spec"

set "WORK=%PROJECT_ROOT%\build_cache"

set "DIST=%PROJECT_ROOT%"

set "EXE=%DIST%\CapiLauncher.exe"

set "ROOT_EXE=%PROJECT_ROOT%\CapiLauncher.exe"

set "PYINSTALLER=%PROJECT_ROOT%\.venv\Scripts\pyinstaller.exe"



set "STEP=[1/6] Validando entorno"

echo %STEP%

if not exist "%SPEC_DIR%\%SPEC%" (

    echo [ERROR] No se encontro el archivo de especificacion: "%SPEC_DIR%\%SPEC%"

    exit /b 1

)



set "STEP=[2/6] Limpiando artefactos previos"

echo %STEP%

if exist "%WORK%" rd /s /q "%WORK%" >nul 2>&1

if not exist "%WORK%" mkdir "%WORK%" >nul 2>&1

if exist "%EXE%" del /f /q "%EXE%" >nul 2>&1

if exist "%ROOT_EXE%" del /f /q "%ROOT_EXE%" >nul 2>&1



if not exist "%PYINSTALLER%" (

    set "PYINSTALLER=pyinstaller"

)



set "STEP=[3/6] Ejecutando PyInstaller"

echo %STEP%

pushd "%SPEC_DIR%" >nul

"%PYINSTALLER%" --distpath "%DIST%" --workpath "%WORK%" %SPEC% --clean

set "RESULT=%ERRORLEVEL%"

popd >nul



if exist "%WORK%" rd /s /q "%WORK%" >nul 2>&1

if not exist "%EXE%" (
    if exist "%DIST%\CapiLauncher\CapiLauncher.exe" set "EXE=%DIST%\CapiLauncher\CapiLauncher.exe"
)

if not "%RESULT%"=="0" (

    echo [ERROR] PyInstaller devolvio codigo %RESULT%

    exit /b %RESULT%

)



set "STEP=[4/6] Verificando artefacto"

echo %STEP%

if not exist "%EXE%" (

    echo [ERROR] No se genero "%EXE%"

    exit /b 1

)



set "STEP=[5/6] Publicando ejecutable en la raiz"

echo %STEP%

if /I "%EXE%"=="%ROOT_EXE%" (

    echo Ejecutable generado directamente en "%ROOT_EXE%"

) else (

    move /y "%EXE%" "%ROOT_EXE%" >nul

    if errorlevel 1 (

        echo [ERROR] No se pudo copiar el ejecutable a "%ROOT_EXE%"

        exit /b 1

    )

    if exist "%EXE%" (

        echo [ERROR] El ejecutable sigue presente en "%EXE%"

        exit /b 1

    )

)

if not exist "%ROOT_EXE%" (

    echo [ERROR] No se encuentra "%ROOT_EXE%" tras publicar el ejecutable

    exit /b 1

)
set "STEP=[6/6] Build completado"

echo %STEP%

echo Capi Launcher disponible en "%ROOT_EXE%"

exit /b 0

