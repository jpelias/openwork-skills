# Herramientas de Reverse Engineering

B17428_02_ePub Chapter 2 : Setting Up a Mobile App Reverse Engineering Environment Using Modern Tools As you already understand the fundamentals of reverse engineering, let s start exploring some modern reverse engineering tools that can be used for mobile applications.

In order to reverse engineer mobile apps, we need specialized tools and utilities.

Some of those tools are paid and some are open source.

We will try to use the open source tools and utilities as much as possible, but will also provide you with a commercial alternative, wherever applicable.

Before we start setting up the tools in our newly created Ubuntu virtual machine, it is important to understand that some of the tools work for both iOS and Android apps, while some of them only work on one.

For each tool explained, you will find a Use case example section.

This section will provide information about what platform this tool will work on, that is, iOS/Android or both.

At the end of the chapter, you will also be provided with details about a customized virtual machine platform for penetration testing and the reverse engineering of mobile applications, Mobexler.

This chapter talks about some of the fun little utilities, as well as commercial tools, that can be used for reverse engineering.

In this chapter, we will cover the following topics: Tools for the reverse engineering of mobile (Android and iOS) applications Setting up an environment for reverse engineering Installing and setting up the tools for reverse engineering Setting up Mobexler (a mobile application penetration testing platform) Technical requirements Download and set up a virtual machine (at the time of writing this book, Ubuntu 20.04.3 LTS is the latest version, and we will be using that) using any virtualization software, such as VirtualBox or VMware.

You can download Ubuntu 20.04.3 LTS (Ubuntu desktop) at https://ubuntu.com/download/desktop.

For virtualization, you can use the open source VirtualBox ( https://www.virtualbox.org/ ) or the commercially available version (as well as the free version) of VMware Workstation Player ( https://www.vmware.com/in/products/workstation-player.html ) for Windows, or VMware Player Fusion ( https://www.vmware.com/in/products/fusion.html ) for Mac.

The steps to download and set up a virtual machine are not covered, as it is a straightforward and easy-to-do task.

Following any good article/blog post on how to set up an Ubuntu virtual machine should provide all necessary information.

Here is a post from the VirtualBox official website about creating a Windows-based virtual machine: https://www.virtualbox.org/manual/ch01.html#gui-createvm.

Tools for the reverse engineering of mobile applications We learned in the last chapter that Android apps, as well as iOS apps, come in a specific format (APK or IPA), which is nothing but a compressed ( .zip ) version of all the application files and most importantly the compiled binary file.

When we start with the reverse engineering of mobile apps, the primary goal is to understand the internals of the application, including its features and implemented security controls, and reconstruct as much original code as possible.

To do this in a mobile application, the first step is to decompress or, more specifically, decompile the application package itself.

When you start, the first step is to get the application package (APK or IPA) and decompress it.

To do that, you need a simple utility that decompresses a compressed file ( .zip ).

Some such utilities come preinstalled with most Linux operating systems.

Just start your newly created Ubuntu virtual machine and start Terminal.

To use the unzip utility, type the following in Terminal: # unzip --help The preceding command should result in running the unzip utility and showing you all the different options available.

Now, let s try and unpack an APK file.

Simply take the APK file we created in the previous chapter and try to unpack it using the unzip utility.

Make sure the APK file is saved in the Desktop folder, or create a new folder and save the file in that folder.

Once the file is saved, open Terminal in that folder by right-clicking somewhere inside it and selecting Open in Terminal.

Rename the APK file to ZIP: #mv app-debug.apk app-debug.zip Extract the files from the ZIP file using the unzip utility: #unzip app-debug.zip The extracted files are as follows: Figure 2.1 – Running the unzip utility to unzip an APK file Even though you can unzip the APK/IPA and explore the files inside it, for Android, this is not the correct way to start with reverse engineering.

For example, once extracted, if you try and view the AndroidManifest.xml file, it will not be readable.

This is because at this point, you have simply inflated compiled sources, and editing or viewing a compiled file is not that easy.

This is where the use of the apktool tool comes into play.

To start with the reverse engineering of an Android application, the correct approach is by using apktool , which can properly decode APK resources to almost the original form and rebuild them after making some modifications.

The decode option in apktool will convert important files, such as config and resources, to XMLs.

As we just saw, the reverse engineering of iOS and Android apps requires very specific modern tools.

So, let s look at some of those tools and set them up in a virtual machine environment.

After the installation and setup of all these tools, we will have a fresh, ready-to-use environment for the reverse engineering of mobile apps (both Android and iOS apps).

apktool Tool: apktool Website: https://ibotpeaches.github.io/Apktool/install/ About: A tool for reverse engineering Android apps Used for: Android apps Here are the instructions to install apktool (in Ubuntu): Download the Linux wrapper script (right-click and select Save Link As apktool ) from this link: https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool : #wget https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool Download apktool-2 (find the current version, 2.6.0): https://bitbucket.org/iBotPeaches/apktool/downloads/.

Rename the downloaded JAR to apktool.jar.

Move both files ( apktool.jar and apktool ) to /usr/local/bin (root needed).

Make sure both files are executable ( chmod +x ).

Try running apktool via the CLI: Figure 2.2 – Setting up apktool If you see an error related to Java, it might be possible that Java is not installed.

In that case, please install Java with the following command: #sudo apt install default-jdk #sudo apt install default-jre Use case example apktool is probably the first tool you will use when starting to reverse engineer an Android application package.

apktool is used to first decode the original Android package and extracts all the files from inside it together with the dex files.

Let s have a look at how it can be used to decode an APK and get all its components: Once installed, we will simply start Terminal and type the following command: #apktool d APK Path Here, d stands for decode.

Here is the snippet for reference: Figure 2.3 – Using apktool When the decoding completes, all the components of the APK will be saved inside a folder with the same name as the package: Figure 2.4 – Decoded application components JADX – Dex-to-Java decompiler Tool: JADX – Dex-to-Java decompiler Website: https://github.com/skylot/jadx About: Command line and GUI tools for producing Java source code from Android dex and APK files Used for: Android apps Follow these instructions to install it (in Ubuntu): Download the latest available version of the tool from https://github.com/skylot/jadx/releases/.

The downloaded file will be a ZIP; extract it to a folder.

Navigate to the folder where you have extracted the file and go inside the bin folder.

To use the GUI version of the application, run the following: #./jadx-gui The result is as follows: Figure 2.5 – Running jadx-gui Use case example JADX is a great tool, as it takes an Android package (APK) as the input and then provides the Java source code as the output.

It takes care of decoding the APK and then converting the dex files to JAR files, which are then interpreted in the reader.

Let s load the APK we created directly into the jadx-gui application and look at the output: Figure 2.6 – JADX showing the Java source code from the APK smali/baksmali Tool: smali/baksmali Website: https://github.com/JesusFreke/smali About: An assembler/disassembler for the dex format used by Dalvik Used for: Android apps Follow these instructions to install it (in Ubuntu): Download and save the latest stable version of the tool from https://bitbucket.org/JesusFreke/smali/downloads/.

Use Java to run either of the apps.

For example, run baksmali as shown in the following figure: Figure 2.7 – Using baksmali to disassemble an APK strings Tool: strings Website: https://www.gnu.org/software/binutils/.

About: The Linux strings command is primarily used for finding string characters in files.

It focuses on determining the contents of, and extracting text from, binary files (non-text files).

Different operating systems might have different arguments.

Used for: Android and iOS apps To install it (in Ubuntu), run the following command in Terminal: #sudo apt-get install binutils The screenshot for reference is as follows: Figure 2.8 – Running strings Use case example The strings utility is very helpful when you are trying to find a static string in the application binary.

Just pass the binary as input to the strings utility and it will extract all the strings from it.

Looking at the extracted strings is very helpful, as it can provide the class names, method names, static text, and hardcoded information, for example.

Let s zip extract (change the extension to .zip and extract using any zip extractor tool) the APK file we have, and then run strings on the classes.dex file.

This should extract all the strings inside the dex file.

Run the $strings classes.dex command and it will extract all the strings.

You can also save all the extracted strings by using output redirection with $strings classes.dex extracted_strings.txt.

Ghidra Tool: Ghidra Website: https://github.com/NationalSecurityAgency/ghidra/releases.

About: A software reverse engineering ( SRE ) suite of tools developed by the NSA s Research Directorate Used for: Primarily iOS apps Follow these instructions to install it (in Ubuntu): Download the latest release from https://github.com/NationalSecurityAgency/ghidra/releases.

Extract the ZIP file to any folder.

Navigate to the folder where the ZIP file was extracted and run the following command in Terminal: #./ghidraRun The screenshot for reference is as follows: Figure 2.9 – Running Ghidra Once you start Ghidra, create a project and then choose one of the tools to run, as shown here: Figure 2.10 – Starting the CodeBrowser Ghidra tool The CodeBrowser tool helps in disassembling binary files.

You can import the classes.dex file (just drag and drop) and the tool will show the disassembled code.

Figure 2.11– Starting the CodeBrowser Ghidra tool Radare Tool: Radare Website: https://rada.re/r/.

About: Disassembling (and assembling) many different architectures Used for: Primarily iOS apps Follow these instructions to install it (in Ubuntu): Run the following commands in Terminal: #sudo apt-get update #sudo apt-get install radare2 Once installed, run the following command to confirm: #radare2 –version The screenshot for reference is as follows: Figure 2.12 – Running radare2 So far, we have completed the installation and setup of all the main tools required for the reverse engineering of mobile apps, although some more tools might be needed in the chapters ahead.

We will install those utilities/tools when required.

Installing and updating the various tools and utilities that are required for reverse engineering can be a big task.

Penetration testers and reverse engineers need a proper setup for their work every day.

What if there was a customized, well-set-up, and prebuilt platform for the security testing and reverse engineering of mobile apps? Well, here comes Mobexler , a mobile application penetration testing platform.

Mobexler comes preinstalled with all the necessary tools and utilities that are required by penetration testers and reverse engineers.

Mobexler is specifically made to help in the security testing of Android apps as well as iOS apps.

However, when starting with any new topic, it is always best to spend some extra time and set up everything manually.

We will be using the Ubuntu virtual machine environment for the rest of the book, but once you are comfortable with all the tools and understand their usage, feel free to use a pre-set-up environment, such as Mobexler.

Mobexler virtual machine About: A mobile application penetration testing platform that comes preinstalled with all the tools required for the reverse engineering and penetration testing of Android and iOS applications Website: https://mobexler.com/ Used for: Android and iOS Follow these instructions to set it up: Download the latest image ( ova ) file from the Mobexler website: https://mobexler.com/download.htm.

Import the downloaded virtual machine image in virtualization software, such as VirtualBox or VMware.

You can also follow the step-by-step guide on the Mobexler website: https://mobexler.com/setup.htm.

Once imported as a virtual machine, log in to the virtual machine using the password mentioned in the virtual machine description.

To learn more about the tools installed inside Mobexler, you can visit the Mobexler page at https://mobexler.com/tools.htm.

Use case example As mentioned, Mobexler comes preinstalled with all the main tools you need.

So, it can be used for almost all kinds of mobile apps, such as Java, Kotlin, Swift, and Objective C.

For example, let s take the same APK we created in the last chapter and try to use different tools from within Mobexler.

In the following image, we are going to run apktool , which is preinstalled in Mobexler, and decode an APK file.

The APK file used is the same sample APK created in the previous section of this book.

You can use the same command to decompile any other APK as well.

The command is as follows: #apktool d [apk_nam/path] Here, d stands for decode.

The screenshot for reference is as follows: Figure 2.13 – Using apktool in Mobexler to decode an APK Similarly, you can use other more advanced tools, such as radare2, right from the Mobexler Terminal: Figure 2.14 – Using apktool in Mobexler Now that we have got the environment fully set up for the reverse engineering of mobile apps, we will start working on some exercises in which we will reverse engineer real-world mobile apps.

In order to help you understand the concepts better, we will be providing the source code (as well as the application package) of a real-world application.

This application will be available in multiple formats, that is, Java and Kotlin for Android applications, and Swift and Objective C for iOS apps.

Summary In this chapter, we looked at some of the awesome utilities and tools that can be used for the purpose of reverse engineering Android and iOS applications.

Knowing how to use these tools and when to use them helps in properly reverse engineering apps.

As you have a reverse engineering environment ready with all the tools, either using an Ubuntu virtual machine or using Mobexler, we can now proceed to actually use these tools and reverse engineer a real Android or iOS application.

In the next chapter, we will start with a more in-depth analysis of a Java-based Android application, where we will try to reverse engineer the application, look inside the source code, and understand its different features.

For the purpose of this book, we have created an Android, as well as an iOS, version of an app called SecureStorage.

In the next chapter, let s look at what the SecureStorage app is about and how we can reverse engineer it..

