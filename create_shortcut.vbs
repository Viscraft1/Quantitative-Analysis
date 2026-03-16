Option Explicit

Dim WshShell
Dim fso
Dim strDesktop
Dim strCurrentDir
Dim strStartIcon

Set WshShell = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strDesktop = WshShell.SpecialFolders("Desktop")
strCurrentDir = fso.GetParentFolderName(WScript.ScriptFullName)
strStartIcon = ResolveStartIcon()

CreateShortcut _
    strDesktop & "\Quant Platform.lnk", _
    strCurrentDir & "\start.bat", _
    strCurrentDir, _
    "Open Quant Platform", _
    strStartIcon

CreateShortcut _
    strDesktop & "\Stop Quant Platform.lnk", _
    strCurrentDir & "\stop.bat", _
    strCurrentDir, _
    "Stop Quant Platform background service", _
    "shell32.dll,28"

WScript.Echo "Desktop shortcuts refreshed."


Function ResolveStartIcon()
    Dim fallbackIcon
    Dim providedIcon
    Dim shortcutIconDir
    Dim folder
    Dim file
    Dim latestFile
    Dim latestTime

    fallbackIcon = strCurrentDir & "\quant_icon.ico"

    If WScript.Arguments.Count > 0 Then
        providedIcon = WScript.Arguments(0)
        If fso.FileExists(providedIcon) Then
            ResolveStartIcon = providedIcon & ",0"
            Exit Function
        End If
    End If

    shortcutIconDir = strCurrentDir & "\.runtime\shortcut_icons"
    If fso.FolderExists(shortcutIconDir) Then
        Set folder = fso.GetFolder(shortcutIconDir)
        latestFile = ""
        latestTime = CDate("2000-01-01 00:00:00")

        For Each file In folder.Files
            If LCase(fso.GetExtensionName(file.Name)) = "ico" Then
                If latestFile = "" Or file.DateLastModified > latestTime Then
                    latestFile = file.Path
                    latestTime = file.DateLastModified
                End If
            End If
        Next

        If latestFile <> "" Then
            ResolveStartIcon = latestFile & ",0"
            Exit Function
        End If
    End If

    If fso.FileExists(fallbackIcon) Then
        ResolveStartIcon = fallbackIcon & ",0"
    Else
        ResolveStartIcon = "shell32.dll,23"
    End If
End Function


Sub CreateShortcut(shortcutPath, targetPath, workingDirectory, description, iconLocation)
    Dim shortcut

    Set shortcut = WshShell.CreateShortcut(shortcutPath)
    shortcut.TargetPath = targetPath
    shortcut.WorkingDirectory = workingDirectory
    shortcut.WindowStyle = 1
    shortcut.Description = description
    shortcut.IconLocation = iconLocation
    shortcut.Save
End Sub
