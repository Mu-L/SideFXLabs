# Installation

Platform-specific details are noted where they differ.

## Method 1 (Personal): Houdini Launcher

Open **Houdini Launcher** and navigate to the **Labs/Packages** section to install a version of SideFX Labs.

The SideFX Labs package will be installed to the following location depending on your OS:

| OS | Default Install Path |
|----|----------------------|
| Windows | `C:\Program Files\Side Effects Software\sidefx_packages` |
| Linux | `/opt/sidefx/sidefx_packages` |
| macOS | `/Applications/Houdini/sidefx_packages` |

Please note that if you have (perhaps accidentally) installed multiple copies of the same version of SideFX Labs (e.g. SideFXLabs21.0), the copy located in `sidefx_packages` will typically take precedence.

## Method 2 (Deployment): Command Line

You can also install the SideFX Labs package through command line. This is especially useful for deployment in a studio environment.

### Windows

Use **Command Prompt** or **Houdini Command Line Tools** (`C:\Program Files\Side Effects Software\Houdini 21.0.100\bin\hcmd.exe`).

To install the latest production build, the latest daily build, or to uninstall (listed in this order), the commands are:
```
"C:\Program Files\Side Effects Software\Launcher\bin\houdini_installer.exe" install-package --package-name "SideFX Labs 21.0 Production Build" --installdir "D:\studio\sidefxlabs"

"C:\Program Files\Side Effects Software\Launcher\bin\houdini_installer.exe" install-package --package-name "SideFX Labs 21.0 Daily Build" --installdir "D:\studio\sidefxlabs"

"C:\Program Files\Side Effects Software\Launcher\bin\houdini_installer.exe" uninstall-package "D:\studio\sidefxlabs\SideFXLabs21.0.json"
```
(`D:\studio\sidefxlabs` is just an example path.)

To replace part of a hard-coded path with an environment variable, you need to first define the environment variable on the machine that executes the commands.

Press the Windows key to search for **Edit environment variables for your account**, and then click **New...** on the **Environment Variables** window to add a new variable.

Please note that Houdini-specific environment variables, such as `HSITE`, `HOME`, etc., are not automatically recognized in **Command Prompt** or **Houdini Command Line Tools** when you type in commands. For command line installation purposes, adding environment variables to `houdini.env` or a Houdini package definition JSON file is not enough. You have to define them in the system.

Once the environment variable is set (e.g. `MY_SIDEFXLABS = D:\studio\sidefxlabs`), then the commands become:

```
"C:\Program Files\Side Effects Software\Launcher\bin\houdini_installer.exe" install-package --package-name "SideFX Labs 21.0 Production Build" --installdir "%MY_SIDEFXLABS%"

"C:\Program Files\Side Effects Software\Launcher\bin\houdini_installer.exe" install-package --package-name "SideFX Labs 21.0 Daily Build" --installdir "%MY_SIDEFXLABS%"

"C:\Program Files\Side Effects Software\Launcher\bin\houdini_installer.exe" uninstall-package "%MY_SIDEFXLABS%\SideFXLabs21.0.json"
```

### Linux

Use a terminal. The Houdini Launcher installer is typically located at `~/houdini_launcher/bin/houdini_installer`.

```bash
~/houdini_launcher/bin/houdini_installer install-package --package-name "SideFX Labs 21.0 Production Build" --installdir "/studio/sidefxlabs"

~/houdini_launcher/bin/houdini_installer install-package --package-name "SideFX Labs 21.0 Daily Build" --installdir "/studio/sidefxlabs"

~/houdini_launcher/bin/houdini_installer uninstall-package "/studio/sidefxlabs/SideFXLabs21.0.json"
```
(`/studio/sidefxlabs` is just an example path.)

To use an environment variable instead of a hard-coded path, define it in your shell profile (e.g. `~/.bashrc` or `~/.zshrc`):

```bash
export MY_SIDEFXLABS=/studio/sidefxlabs
```

Then reload your shell (`source ~/.bashrc`) and use the variable in your commands:

```bash
~/houdini_launcher/bin/houdini_installer install-package --package-name "SideFX Labs 21.0 Production Build" --installdir "$MY_SIDEFXLABS"

~/houdini_launcher/bin/houdini_installer install-package --package-name "SideFX Labs 21.0 Daily Build" --installdir "$MY_SIDEFXLABS"

~/houdini_launcher/bin/houdini_installer uninstall-package "$MY_SIDEFXLABS/SideFXLabs21.0.json"
```

As with Windows, Houdini-specific environment variables (e.g. `HSITE`, `HOME`) are not automatically recognized at the command line for installation purposes. You must define them at the system or shell profile level.

### macOS

Use **Terminal**. The Houdini Launcher installer is typically located at `/Applications/HoudiniLauncher.app/Contents/MacOS/houdini_installer`.

```bash
/Applications/HoudiniLauncher.app/Contents/MacOS/houdini_installer install-package --package-name "SideFX Labs 21.0 Production Build" --installdir "/studio/sidefxlabs"

/Applications/HoudiniLauncher.app/Contents/MacOS/houdini_installer install-package --package-name "SideFX Labs 21.0 Daily Build" --installdir "/studio/sidefxlabs"

/Applications/HoudiniLauncher.app/Contents/MacOS/houdini_installer uninstall-package "/studio/sidefxlabs/SideFXLabs21.0.json"
```
(`/studio/sidefxlabs` is just an example path.)

To use an environment variable instead of a hard-coded path, define it in your shell profile (e.g. `~/.zshrc` for the default macOS shell):

```bash
export MY_SIDEFXLABS=/studio/sidefxlabs
```

Then reload your shell (`source ~/.zshrc`) and use the variable in your commands:

```bash
/Applications/HoudiniLauncher.app/Contents/MacOS/houdini_installer install-package --package-name "SideFX Labs 21.0 Production Build" --installdir "$MY_SIDEFXLABS"

/Applications/HoudiniLauncher.app/Contents/MacOS/houdini_installer install-package --package-name "SideFX Labs 21.0 Daily Build" --installdir "$MY_SIDEFXLABS"

/Applications/HoudiniLauncher.app/Contents/MacOS/houdini_installer uninstall-package "$MY_SIDEFXLABS/SideFXLabs21.0.json"
```

As with Windows, Houdini-specific environment variables are not automatically recognized at the command line for installation purposes. You must define them at the system or shell profile level.

---

For more on how to download, install, upgrade, and uninstall Houdini and its components, please visit [here](https://www.sidefx.com/docs/houdini/ref/utils/launcher.html).

## Method 3 (Specific Versions / Steam Houdini Users): GitHub

Sometimes you may need to access an earlier release or to get the same-day updates before the next day's release is downloadable. In those cases, you can get the package directly from this GitHub repository.

Step 1a. [Option A] Download one of the releases from [here](https://github.com/sideeffects/SideFXLabs/releases). Choose a release version/date, expand **Assets** and select either one of the **Source code** zip files. This step can be automated with a script that downloads the zip files from either one of the following URLs (replace 21.0.100 with the desired version number).

```
https://github.com/sideeffects/SideFXLabs/archive/refs/tags/21.0.100.zip
https://github.com/sideeffects/SideFXLabs/archive/refs/tags/21.0.100.tar.gz
```

Step 1b. [Option B] Click on the top-right **Code** button on the main page of this repository and select **Download ZIP**. This allows you to get the same-day updates before the next day's release is downloadable.

Step 1c. [Option C] (Advanced) Clone this repository into a custom SideFXLabs directory of your choosing. Skip Step 2.

Step 2. If you have downloaded a zipped version of the package in Step 1, unzip it into a custom SideFXLabs directory of your choosing.

Step 3. Go to your custom SideFXLabs directory that now contains the unzipped contents, copy the package definition template file `SideFXLabs.json` to the appropriate Houdini packages folder for your OS:

| OS | Packages Folder |
|----|-----------------|
| Windows | `C:\Users\...\Documents\houdini21.0\packages` |
| Linux | `~/houdini21.0/packages` |
| macOS | `~/Library/Preferences/houdini/21.0/packages` |

Rename the destination copy to `SideFXLabs21.0.json`. Open this file and replace `"$HOUDINI_PACKAGE_PATH/SideFXLabs21.0"` with the path to your own SideFXLabs directory. When Houdini launches, it relies on this file to discover the location of your SideFX Labs package.

> **Note:** Step 3 only needs to be done once for every major Houdini X.Y release. To update SideFX Labs for the same Houdini X.Y version, simply delete the existing contents of your custom SideFXLabs directory and unzip the updated package into that folder.

For more on how to manage Houdini packages, please visit [here](https://www.sidefx.com/docs/houdini/ref/plugins.html).

## Verification
If SideFX Labs is successfully installed, launch Houdini and you should see a **Labs** menu on the menu bar.

# Additional Information

## Live Development
We're actively developing the tools in this repository. The [releases](https://github.com/sideeffects/SideFXLabs/releases) provide safe checkpoints in the code for you to download.

## Other Environment Variables
SideFX Labs has a few other environment variables that can be set to modify the behavior of the toolset and its installation process:
1. `SIDEFXLABS_NOINSTALL_MESSAGE=Your message here` - Disables the installing of the toolset on the machine, and shows the text stored in the environment variable.
2. `SIDEFXLABS_ADMIN_UPDATES=1` - This prevents users from updating the already installed toolset on their machine. Useful for studios where one version of the toolset is enforced.
