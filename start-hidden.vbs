' Startet TabDeck unsichtbar im Hintergrund (ohne Konsolenfenster).
' Vorher einmal start.bat ausfuehren, damit alles installiert ist.
' Fuer Autostart: Win+R -> shell:startup -> Verknuepfung zu dieser Datei hineinlegen.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = dir & "\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(pyw) Then
  MsgBox "Bitte zuerst start.bat einmal ausfuehren.", 48, "TabDeck"
  WScript.Quit 1
End If
sh.CurrentDirectory = dir
sh.Run """" & pyw & """ -m server", 0, False
