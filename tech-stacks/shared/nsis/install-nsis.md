# Installing NSIS without admin rights

`makensis` is the only thing the installer build needs (`wails3 package`, or
`makensis` called from `scripts/package.ps1`). The official setup wants
elevation to write under `Program Files`, and winget/Chocolatey machine-wide
installs want it too. The **zip distribution does not**: it is the same
compiler, relocatable, and nothing is written outside the folder you unpack.

1. Download `nsis-<version>.zip` (not the `-setup.exe`) from
   <https://sourceforge.net/projects/nsis/files/NSIS%203/>. Take the newest
   3.x; check the SHA-256 against the value SourceForge shows beside the file.
2. Unpack it into a folder of your own, and unblock it first: a zip downloaded
   through a browser carries the mark-of-the-web and Windows may refuse the
   extracted `makensis.exe`.

   ```powershell
   $zip  = "$env:USERPROFILE\Downloads\nsis-3.11.zip"   # the file you downloaded
   $dest = "$env:LOCALAPPDATA\Programs\NSIS"
   Unblock-File $zip
   Expand-Archive $zip -DestinationPath "$env:TEMP\nsis-unpack" -Force
   Move-Item "$env:TEMP\nsis-unpack\nsis-*" $dest      # the zip holds one nsis-<version>\ folder
   ```
3. Put it on the **user** `PATH` (no admin needed), then open a new terminal:

   ```powershell
   # Not [Environment]::SetEnvironmentVariable: it expands every %VAR% in the
   # value and writes it back as plain text. Edit the registry value as it is.
   $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true)
   $p   = $key.GetValue('Path', '', 'DoNotExpandEnvironmentNames')
   if (($p -split ';') -notcontains $dest) {
       $key.SetValue('Path', ($p.TrimEnd(';') + ";$dest"), 'ExpandString')
   }
   $key.Close()
   ```
4. Check: `makensis /VERSION` prints `v3.xx`. `makensis` finds its `Include/`,
   `Plugins/` and `Stubs/` next to itself, so the folder must stay whole.

Notes:

- Upgrading is the same steps into a fresh folder; delete the old one after.
- The unpacked tree is third-party binaries: keep it out of the repository.
- Where a download from SourceForge is blocked (`corporate-proxy.md`), ask
  for the zip to be fetched for you rather than disabling TLS verification.
- If the user `PATH` is a pain to edit, call the compiler by its full path
  instead (`& "$env:LOCALAPPDATA\Programs\NSIS\makensis.exe" ...`).
