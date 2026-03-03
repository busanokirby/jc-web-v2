Set objFSO = CreateObject("Scripting.FileSystemObject")
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

Set objShell = CreateObject("WScript.Shell")
objShell.Run "cmd /c cd /d """ & strPath & """ && webv2\Scripts\activate.bat && webv2\Scripts\waitress-serve.exe --host 0.0.0.0 --port 5000 wsgi:app", 0, False