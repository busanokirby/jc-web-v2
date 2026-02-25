Set objFSO = CreateObject("Scripting.FileSystemObject")
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

Set objShell = CreateObject("WScript.Shell")
objShell.Run "cmd /c cd /d """ & strPath & """ && webv2\Scripts\activate.bat && waitress-serve --host 0.0.0.0 --port 8080 wsgi:app", 0, False