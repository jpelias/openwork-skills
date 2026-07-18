# Fundamentos de Reverse Engineering

B17428_01_ePub Chapter 1 : Basics of Reverse Engineering – Understanding the Structure of Mobile Apps All of us use cell phones in our daily lives now, and their usage has grown to such a crucial level that people frequently name cell phones as one of the three things you can t live without , after food and water.

Cell phones handle almost every task, from managing funds in bank accounts and investments to travel bookings, shopping, and health appointments.

To perform these tasks, cell phones have mobile apps.

These apps handle a majority of your data and help you perform tasks.

As these modern mobile apps handle sensitive user information, perform critical tasks, and provide access to a huge array of resources on the internet, the security of the data being handled and the operations performed on it also need to be improved.

A mobile application penetration tester tests the security of mobile applications in order to find vulnerabilities.

To find the vulnerabilities, the tester is required to understand the internal working and logics of the application.

These details can be found in the source code of the application.

However, the penetration testers do not always have the source code to hand, as in the case of a black-box penetration test.

During a black-box penetration test, all that the penetration tester has is the application package, that is, the Android Application Package ( APK ) or iOS App Store Package ( IPA ) file.

In such a case, to understand the working of the app, they need to unpack the application package and get the source code.

Reverse engineering is the technique of dismantling an object to study its internal designs, code, logic, and so on.

Reverse engineering mobile applications is the process of disassembling/dismantling an app to reveal its code and internal logic, components, and so on.

In this chapter, we re going to cover the following main topics: Reverse engineering fundamentals Android application fundamentals iOS application fundamentals We will learn about the basics of reverse engineering and how mobile applications are built.

These fundamentals are important to understand before we can jump into the actual task of reverse engineering modern apps.

Technical requirements Android Studio and Xcode are required to complete the relevant hands-on exercises.

Xcode is Apple s integrated development environment ( IDE ) for macOS, used to develop software for macOS, iOS, iPadOS, watchOS, and tvOS.

Android Studio is the official IDE for Google s Android operating system.

An Apple laptop/desktop (Mac) can install and run both Xcode and Android Studio, whereas other laptops/desktops running Windows or Linux will only be able to support Android Studio.

For more information, please refer to the following links: Android Studio: https://developer.android.com/studio Xcode: https://developer.apple.com/xcode/ Reverse engineering fundamentals Let s first understand the fundamentals of reverse engineering, why it is needed, and what steps are involved.

As mentioned earlier in this chapter, reverse engineering is the technique of dismantling an object to study its internal designs, code, and logic.

When a developer builds a mobile app, they choose a programming language (according to the targeted platform – Android, iOS, or both), write the code for the functionalities they want, and add resources such as images, certificates, and so on.

Then the code is compiled to create the application package.

While reverse engineering the same app, the reverse engineer dismantles the application package to the components and code.

Some of the frequently used terms in reverse engineering are the following: Decompilation : This is the process of translating a file from a low-level language to a higher level language.

The tool used to perform decompilation is called a decompiler.

A decompiler takes a binary program file and changes this program into a higher-level structured language.

The following diagram illustrates the decompilation process: Figure 1.1 – Diagram of the decompilation process Disassembling : This is the process of transforming machine code (in an object code binary file) into a human-readable mnemonic representation called assembly language.

The tool used to perform disassembly is called a disassembler as it does the opposite of what an assembler does.

The following diagram illustrates the disassembly process: Figure 1.2 – Diagram of the disassembly process A simple binary disassembled in a disassembling tool, Hopper, looks as fol lows: Figure 1.3 – Disassembled binary in Hopper Debugging : This is a technique that allows the user to view and modify the state of a program at runtime.

The following diagram illustrates the debuggi ng process: Figure 1.4 – Diagram of the debugging process Understanding the different methodologies and approaches used in reverse engineering is very important.

We will be using all these concepts in further chapters of this book.

Now that we have seen the fundamentals of reverse engineering, let s explore how mobile applications, that is, Android and iOS apps, are developed.

We will now be looking into the components, structure, and concepts behind the mobile application fundamentals.

Android application fundamentals Native Android applications are written mainly in Java or Kotlin.

The Android SDK tools compile the code along with any data and resource files into an APK or an Android App Bundle.

The compiled application is in a specific format, specified by the extension .apk.

That is, an Android package is an archive file containing multiple application files and metadata.

Fun Fact Rename the file extension of an APK to .zip and use unzip to open.

You will be able to see it s contents.

The following are the major components of an APK: AndroidManifest.xml : The application manifest file containing app details such as the name, version, referenced libraries, and component details in XML format.

The Android operating system relies on the presence of this file to identify relevant information about the application and related files.

Dalvik executable files ( classes.dex files).

META-INF : MANIFEST.MF (manifest file) CERT.RSA (certificate of the application) CERT.SF (list of resources with SHA-1 digest of the corresponding lines in the MANIFEST.MF file) lib : This contains the compiled code that is specific to a selection of processors, as follows: armeabi : Compiled code for all ARM-based processors armeabi-v7a : Compiled code for all processors based on ARMv7 and above x86 : Compiled code for x86 processors mips : Compiled code for MIPS processors res : Resources that are not compiled into resources.arsc.

assets : Contains application assets.

resources.arsc : Pre-compiled resources.

Important Note Java code in Android devices does not run in the Java Virtual Machine ( JVM ).

Rather, it is compiled in the Dalvik Executable ( DEX ) bytecode format.

A DEX file contains code that is ultimately execute d by Android Runtime.

Let s see how to create a simple hello world application for Android and then unzip it to look at its components: Android apps are developed using Android Studio.

Download and install the latest version of Android Stu dio from https://developer.android.com/studio : Figure 1.5 – Creating a new project in Android Studio Let s choose the New Project option and select the Empty Activity option: Figure 1.6 – Selecting project type On the next screen, fill in all the details as shown in the following screenshot.

You can choose the name as you please: Figure 1.7 – Project details Once you click Finish , a new project will be created for a default activity/screen app.

You can now try to run the app on any attached Android device, or the virtual Android emulator.

For the latter, create a virtual Android device from the AVD menu.

Once the app runs successfully, we will try to extract the application package for this app from Android Studio: Figure 1.8 – Running the app on the emulator To get the APK from Android Studio, go to the Build | Build Bundle(s)/APK(s) | Build APK(s) menu option.

Once generated, navigate to the folder mentioned in the Locate option and copy the APK.

Once the APK is copied, change the exten sion of the file to .zip : Figure 1.9 – Diagram of rename process Use any archive tool to unzip the fil e and extract its contents: # unzip MARE-Chapter-1.zip For reference, th e result is as follows: Figure 1.10 – Extracting the content of the APK, after renaming it to .zip Let s analyze the components inside the APK and compare it with the list here ( Android application fundamentals ): Figure 1.11 – E xtracted content of the APK The following diagram shows the processes of forward and reverse engin eering an Android application: Figure 1.12 – The forward and reverse engineering processes with an Android application Android applications are mainly developed using Java and Kotlin.

The internals of an Android package are the same whether it is based on Java or Kotlin.

Therefore, the approach to reverse engineer the application is also the same.

We ve now learned about the fundamentals of Android applications.

iOS apps are also packaged into a specific format and have a specific structure.

Let s look into the iOS application fundamentals now.

iOS application fundamentals Similar to Android, iOS applications also come in a specific zipped format called IPA , or an iOS App Store Package.

iOS application packages can also be renamed by changing the extension to ZIP and then the components can be extracted, though the components of an iOS application package differ from those of an Android one.

iOS apps are mainly built using Objective-C and Swift, both of which can be disassembled using a disassembler such as Hopper or Ghidra.

In Objective-C applications, methods are called via dynamic function pointers, which are resolved by name during runtime.

These names are stored intact in the binary, making the disassembled code more readable.

Unlike Android, in iOS, the application code is compiled to machine code that can be analyzed using a disassembler.

The following are the major components of an iOS application package: Info.plist : Similar to the Android manifest file in an APK, this information property list file contains key-value pairs that specify essential runtime-configuration information for the application.

The iOS operating system relies on the presence of this file to identify relevant information about the application and related files.

Executable : The file that runs on the device, containing the application s main entry point and code that was statically linked to the application target.

Resource files : Files that are required by the executable file, and are required for the application to properly run.

This may contain images, nib files, string files, and configuration files.

The following diagram illustrates the iOS architecture overview: Figure 1.13 – iOS architecture Let s see how to create a simple hello world application for iOS and then unzip it and look at its components: iOS apps are developed using Xcode.

Download the latest version of Xcode from the App Store on Mac.

Figure 1.14 – Creating an Xcode project On the next screen, choose the default App template for your new project: Figure 1.15 – Selecting the project template On the next screen, provide a product name (any name you like), select a team, and provide an organization identifier.

To create and export an IPA from Xcode, you need to have an Apple Developer license: Figure 1.16 – Providing project details Select a location to save the project on your computer.

Xcode will now create a simple hello world application and you will see the following default code in the Xcode window: Figure 1.17 – Project details Now you can try and run this app on one of the built-in iOS simulators.

To do so, select one of the available simulators (just click on the name of simulator from top bar, and a list will open) as shown in the following screenshot: Figure 1.18 – Selecting a simulator The app should run on the selected simulator: Figure 1.19 – App running on the simulator Now, let s export the IPA from this Xcode project.

To do so, select the Any iOS Device (arm64) option from the simulator options.

Then, go to Product | Archive and select the Distribute App option: Figure 1.20 – Exporting the application package On the next screen, select Development and leave the options on the subsequent screens at their defaults.

Finally, you will be able to export the IPA together with some other compiled project files: Figure 1.21 – Exporting the application package (cont.) Once the IPA is exported, simply change the extension of the file to .zip : Figure 1.22 – Diagram explaining the application (IPA) extraction process via renaming Use any tool to unzip the file and extract its contents: # unzip MARE-Chapter-1.zip The following screenshot shows the results for reference: Figure 1.23 – Extracting the content of the IPA after renaming it to ZIP Go into the Payload directory and then insid e the MobileAppReverseEngg-App-1.app file: # cd Payload # cd MobileAppReverseEngg-App-1.app Let s analyze the components inside the IPA and compare it with the list here ( iOS application fundamentals ): Figure 1.24 – Extracted content of the IPA The following diagram illustrates the process of reverse engineering an iOS application: Figure 1.25 – Overview of the reverse engineering process of an IPA Have a look at Figure 1.3 to understand how a disassembled binary looks in Hopper disassembler.

Summary The concepts and processes of reverse engineering are very interesting.

Through this chapter, you have learned the fundamentals of reverse engineering both Android and iOS applications.

The concepts explored will help your understanding in the later chapters of this book as we begin to look at reverse engineering in depth.

In the next chapter, we will learn more about the modern tools used to reverse engineer iOS and Android apps..

