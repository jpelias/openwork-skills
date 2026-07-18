# Reverse Engineering de Android

B17428_03_ePub Chapter 3 : Reverse Engineering an Android Application In the last two chapters, you learned about the basics of reverse engineering and looked into some of the tools used and their installation.

You should now be able to create an Ubuntu-based virtual machine environment (or have already done so).

Then, you learned how to install and run the reverse engineering tools listed in Chapter 2 , Setting Up a Mobile App Reverse Engineering Environment Using Modern Tools (only some of the basic operation of the tools was covered, not all the features).

In this chapter, we will be covering the following: Android application development The reverse engineering of Android applications Extracting Java source code Converting .dex files to smali Reverse engineering and penetration testing Code obfuscation in Android apps Technical requirements This chapter has the following technical requirements: An Ubuntu virtual machine with the tools listed in Chapter 2 , Setting Up a Mobile App Reverse Engineering Environment Using Modern Tools (only Android-specific tools).

Download the SecureStorage Android application source code from this link: https://github.com/0ctac0der/SecureStorage-AndroidApp Android application development Before we get into reverse engineering, it is important to understand how the forward-engineering process happens and how an application is developed.

In order to create an application, the developer chooses a programming language according to the operating system on which the application is supposed to run.

For example, in the case of Android applications, generally, a developer may choose to develop their application using Java, Kotlin, or C++ (using other languages is also possible).

Kotlin is the official language for Android applications.

Android Studio is the official development environment for building Android apps.

We already used Android Studio in the Android application fundamentals section of Chapter 1 , Basics of Reverse Engineering – Understanding the Structure of Mobile Apps.

Android Studio contains a comprehensive set of development tools, such as Android Debug Bridge ( ADB ), fastboot , and the Native Development Kit ( NDK ).

The Android software development kit ( SDK ) is fully integrated with Android Studio and can be easily installed using the SDK Manager.

However, we can also use the Android SDK independently without Android Studio.

Refer to the following screenshot, which shows the Android SDK as a part of Android Studio: Figure 3.1 – SDK Manager in Android Studio The developer writes the required code for all the functionalities of the application, its user interface, and the logic for data processing.

Together with the code, all the required resource files, configuration files, and images are also added as a part of the project in Android Studio.

Then, this code (together with the resources) is compiled using the SDK.

Let s say that the code is written in Java.

It will be compiled by the Java compiler ( javac ) into Java bytecode files (class files).

Then, these Java bytecode files are sent to a Java Virtual Machine ( JVM ), which converts them into machine code using a just-in-time ( JIT ) compiler and runs them on the device.

Important Note What is bytecode? To run a Java program on a computer, we need to convert the high-level code (source code or program code) to machine code.

The compiler converts the code from a high-level language to a low-level language; the output of the compilation process is bytecode.

Bytecode is the low-level code, which is mainly the instruction set for software interpreters or virtual machines (such as JVM).

Finally, the bytecode is translated by an interpreter into machine code.

If the code is written in Kotlin, Java-compatible bytecode can be generated using a compiler, such as kotlinc.

Bytecode is nothing but a form of an instruction set executed by a software interpreter.

Previously, Android versions 1.0 to 4.4 had a Dalvik virtual machine to run the apps.

In Android 4.4, Google added Android Runtime ( ART ) together with the Dalvik virtual machine.

The Dalvik virtual machine runs an optimized bytecode format called Dalvik bytecodes.

In the compilation process, the .class files and .jar libraries are converted into classes.dex files containing Dalvik bytecode.

The ART environment also executes .dex files.

Let s summarize this as follows: The developer writes the application code (such as Java or Kotlin) in the Android development environment, Android Studio.

The written code is compiled to Dalvik executable ( .dex ) files using DEX compilers, which will run in the ART environment (as well as the Dalvik virtual machine).

The compilers in Android Studio will also compile the other resource files, JAR libraries, and other libraries (if any).

The compiled .dex files and the compiled resources will be packed together to create the Android Package ( APK ).

Important Note For an Android application developed using Java, the code is compiled to DEX bytecode.

The reverse engineering process works in the opposite direction – extract the .dex files from the APK and convert them to Java code.

The final application package (meaning the APK) will contain the following important files and folders, together with other entities: Resource files in the res folder AndroidManifest.xml A resources.arsc file, which contains all meta-information .dex files In Chapter 2 , Setting Up a Mobile App Reverse Engineering Environment Using Modern Tools , when we simply extracted all the content of an APK file by changing its extension to zip , we found the files listed in the preceding list.

Refer to Chapter 2 , Figure 2.1 – Running the unzip utility to unzip an APK file.

The Android operating system requires that all apps be digitally signed with a certificate before they can be installed.

During the installation process, the Android operating system uses the Package Manager to verify that the APK has been properly signed with the certificate included in that APK.

Developers can use self-signed certificates for signing the applications that they develop.

A developer generates a certificate and uses it to sign the application before a release build is generated.

The certificate file is also a part of the APK.

The reverse engineering of Android applications Let s now look at the ways to reverse engineer Android applications and study the bits that can be extracted from a compiled application package.

In this section, we will be using a specially built application called SecureStorage.

You can download the different builds of the application from the following GitHub links: The debug build of SecureStorage ( https://github.com/0ctac0der/SecureStorage-AndroidApp/releases/download/0.1/app-debug.apk ) The release build of SecureStorage ( https://github.com/0ctac0der/SecureStorage-AndroidApp/releases/download/1.0/app-release.apk ) SecureStorage is a simple Android application that can be used to store credit card information on the device.

A user will have to sign in with the correct password to be able to access the stored information.

You can install the downloaded application on the Android virtual device to see how it works.

Some of the screens look as follows: Figure 3.2 – Home screen of the SecureStorage app If the user does not have an account in the app, they can create an account from the Join Today screen, which looks as follows: Figure 3.3 – Join Today screen of the SecureStorage app Once logged in, users get multiple options to save a credit card, modify an already stored card, and view previously added cards.

The following screen shows all those options: Figure 3.4 – Saved details screen in the SecureStorage app Important Points on the SecureStorage App The application works fully on the client side, which means there is no backend or server side for this application.

As the name suggests, SecureStorage tries to securely store data in the user s device storage.

So far, we have looked into details of how Android apps are developed and run on a device, and their internal components, and have also installed an app (SecureStorage).

Now, let s move forward to start reverse engineering the app and look at what s hidden inside.

Extracting the Java source code The first objective of reverse engineering is to get the original source code with maximum accuracy.

As we have the application package downloaded on our Ubuntu virtual machine, let s use the JADX tool to get the Java code.

However, it might also be a good idea to simply unzip the APK and extract its contents to see what s inside: Figure 3.5 – Extracted contents of the APK In order to use the JADX tool, open the directory where you extracted the JADX .zip file (as explained in Chapter 2 , Setting Up a Mobile App Reverse Engineering Environment Using Modern Tools ).

Once in the directory, right-click to select the Open in Terminal option.

In the opened Terminal window, type the following command to run JADX: # cd bin/ # ./jadx-gui In the JADX window, open the APK file you just downloaded.

Refer to Chapter 2 , Setting Up a Mobile App Reverse Engineering Environment Using Modern Tools , to see how to do this: Figure 3.6 – Decompiled Java source code of the application In the majority of applications, it is possible to reverse engineer the application package to the decompiled Java source code.

However, in some cases, it is possible that the decompiled Java code does not look very clear, or multiple parts of the Java code are not readable at all in the Java decompilers.

Important Note The decompiled Java code from JADX is generally not recompilable.

When code is highly obfuscated, or the Java code is difficult to obtain, we can convert the .dex files (Dalvik bytecode) to smali.

The .dex files contain the binary Dalvik bytecode, which is not at all easy to read or modify, so it is useful to convert that bytecode into a more human-readable format, smali.

So, it is an approach to understand the code through the decompiled code from JADX and use the smali version to edit any part of it and then recompile it.

A pair of tools called smali and baksmali , which are technically an assembler and a disassembler, can be used to convert the smali code to .dex format, and .dex to smali , respectively.

Converting DEX files to smali Let s try to convert the same APK to smali files, using another tool we used in Chapter 2 , Setting Up a Mobile App Reverse Engineering Environment Using Modern Tools.

In order to decompile the APK, run the following command: # apktool d app-debug.apk apktool uses smali / baksmali internally, while decompiling an APK file.

The following figure shows that apktool is decoding the app-debug.apk file provided: Figure 3.7 – Using apktool to decompile the application Once the APK has been decompiled, navigate to the folder created (in this case app-debug ), and you will find several subfolders inside it with the name smali*.

These folders contain the converted smali files from the .dex files in the APK: Figure 3.8 – Decompiled content from apktool Opening any of the smali files will show the respective version of the code.

Let s look at the content of the smali files for the classes5.dex file.

To do so, we will need to navigate to the smali_classes5/com/example/securestorage/adapter directory: # cd smali_classes5/com/example/securestorage/adapter The following figure shows the list of smali files in the directory: Figure 3.9 – smali files for classes4.dex Now, we can read the content of the smali file using the cat utility: # cat CardDetailsAdapter.smali The screenshot for reference is as follows: Figure 3.10 – Reading the smali file for classes4.dex It would also be a good exercise to compare the code in JADX and smali for the same section of the application, CardDetailsAdapter.

The following figure shows a comparison between the Java source code obtained using JADX and the respective smali code for the same section: Figure 3.11 – Comparing the code in JADX and smali Let s summarize what we have done so far: Extracted the content of the APK, by using a tool such as unzip.

This is not the decompiling of the APK but a simple extraction of contents, following the unarchive process.

That s why the compiled resources such as AndroidManifest.xml will not be readable.

(Refer to Figure 3.5 .) Used the JADX tool to get the decompiled Java source code from the APK.

It is easier to use this decompiled code in JADX to understand the functionalities of the application and different classes, for example.

However, if we needed to modify any of the content of this source code, it would be very difficult to recompile it.

Also, JADX might not be able to convert all the .dex files properly to Java code (in readable format).

(Refer to Figure 3.6 .) Decompiled the APK using apktool , which also resulted in getting the smali version of the code.

The smali format is comparatively easy to modify and recompile.

(Refer to Figure 3.7 .) We can also use the smali / baksmali tools independently to convert the .dex files to smali code, and vice versa.

To do so, we can take any of the .dex files from ZIP extracted contents and run baksmali on them.

Let s take the classes4.dex file and copy it to the folder where the smali / baksmali tools are saved: Figure 3.12 – Copying the classes4.dex file to the smali tool folder Now, open the Terminal window in the same folder by right-clicking and selecting the Open in Terminal option.

In the Terminal window, run the following command: # java -jar baksmali-2.5.2.jar disassemble classes4.dex -o app You will see a new directory created with the name app and it will have the smali files located at app/com/example/securestorage/adapter : Figure 3.13 – smali file for classes4.dex Often, reverse engineering is used to find the solution to a specific question, for example, How is this application storing the user information? or How is the application implementing root detection? Let s have a look at a similar case and understand when we can use reverse engineering to find security issues during a penetration test.

Reverse engineering and penetration testing As we have successfully reverse engineered an APK to the Java source code, it is now important to understand why reverse engineering is very important and might be required during penetration testing.

Often in a penetration testing engagement (black box), all that is available to the penetration tester is the name of the application.

The penetration tester downloads the application on a device and extracts the APK.

There might be several cases when it is not evident how certain functions of the application are implemented just by using the app.

In order to find vulnerabilities in the application, it is required to understand how it works.

Reverse engineering helps to answer some of these questions.

Let s take an example.

Imagine you are given a banking application to test (penetration testing).

While using the application, you notice that the application implements a security control that encrypts all the user-submitted data values before sending them as a part of an HTTP request to the backend server.

For example, a login request (HTTP), when captured, might look as follows: POST api/login HTTP/1.1 HOST: applicationdomainname.com Content-Type: application/json { email : 41ZEyV2TFKvkjJwulP7I4hY8qEZaYagik2R6BHJFrPg= , password : crGTh+mckBpwBxXOKTQpWQ== } In this case, it is important to understand how the values of the email and the password are being encrypted to create ciphertext that is being sent as a part of the HTTP request.

The answer to this question might be found by reverse engineering the application and exploring the source code to understand the classes where the encryption of input values is being done.

Similarly, there could be other examples in which different functionalities of the app have a complicated implementation.

In all such cases, reverse engineering the application generally helps in understanding the logic.

As well as that, there are other cases where the reverse engineering of the application can be very much required during a penetration test.

Some of the cases are as follows: Finding the API calls, or endpoints that the application is making to the backend.

Understanding the way some security controls are implemented in order to bypass them.

For example, certificate pinning is a security control implemented in a lot of mobile applications to ensure that an application only establishes the TLS connection using the certificate inside the package, and no external user-installed or system-installed TLS certificate is trusted.

To implement this, the application code verifies that the TLS certificate presented during the SSL handshake is the same as the one stored inside the application package.

One of the common tests performed during root detection is to verify whether an application with the name SuperUser is installed on the device or not.

By reverse engineering the application, a penetration tester can find these types of tests that are being done by the app.

Then, they can modify the corresponding smali file to return a false result and therefore bypass the root detection.

Finding hardcoded sensitive information inside the application code, such as backdoor accounts, API keys and secret, unpublished backend endpoints, and hidden menus.

Finding interesting strings in the code.

Finding points of encryption and obfuscation, so that they can be decrypted and de-obfuscated.

Reverse engineering also helps in learning more about the important components of an application.

A penetration tester would be able to find details of the following components through reverse engineering: Activities : Components that provide a screen with which users can interact.

For example, Figure 3.2 , Figure 3.3 , and Figure 3.4 show the activities of the SecureStorage application.

Broadcast receivers : Components that receive and respond to broadcast messages from other apps or from the operating system.

Services : Components that perform operations in the background.

The majority of these components are listed in the AndroidMinfest.xml file, and the same components can be read/explored from the JADX code or smali files.

Let s look at the AndroidManifest.xml file of the SecureStorage app: Figure 3.14 – AndroidManifest.xml file content The AndroidManifest.xml file mentions that there are five activities in this app: com.example.securestorage.activity.LoginActivity com.example.securestorage.activity.HomeActivity com.example.securestorage.activity.SignupActivity com.example.securestorage.activity.SaveCardInfoActivity com.example.securestorage.activity.CardDetailsActivity We can further explore the implementation of any of these activity components as shown in the following figure in the respective section in JADX: Figure 3.15 – Exploring application activities in JADX We can select an activity and look at the code.

Let s see how SaveCardInfoActivity is implemented: Figure 3.16 – SaveCardInfoActivity Interestingly, if you look at the following section of code, you can see that the application performs some kind of encryption before saving the card details on the device.

It might be interesting to find out how the application encrypts the data submitted and if possible, find a weakness in that section: private void updateCardInfo() { CardInfo cardInfo = new CardInfo(); cardInfo.setCardNumber(SaveDataUtils.getEncryptedData(this.etCardNumber.getText().toString())); cardInfo.setCardExpiry(SaveDataUtils.getEncryptedData(this.etExpirationDate.getText().toString())); cardInfo.setCardCvv(SaveDataUtils.getEncryptedData(this.etCVV.getText().toString())); cardInfo.setCardHolderName(SaveDataUtils.getEncryptedData(this.etCardHolderName.getText().toString())); SaveDataUtils.updateCardInfo(cardInfo, this.itemPosition); CommonUtils.showToast(this, Card Details Edit Successfully ); } /* access modifiers changed from: private */ /* access modifiers changed from: public */ private void saveCardInfo() { SaveDataUtils.addCardInfo(this.etCardNumber.getText().toString(), this.etExpirationDate.getText().toString(), this.etCVV.getText().toString(), this.etCardHolderName.getText().toString()); this.etCardNumber.setText( ); this.etExpirationDate.setText( ); this.etCVV.setText( ); this.etCardHolderName.setText( ); CommonUtils.showToast(this, Card Details Saved Successfully ); } It should also be noted that there is an EncrytionUtils inside the utils section.

EncryptionUtils is called via the getEncryptedData function (inside SaveDataUtils ): public class EncryptionUtils { public static final String password = qkjll5@2md3gs5Q@ ; public static SecretKey generateKey() { return new SecretKeySpec(password.getBytes(), AES ); } public static byte[] encryptMsg(String message) throws NoSuchAlgorithmException, NoSuchPaddingException, InvalidKeyException, IllegalBlockSizeException, BadPaddingException, UnsupportedEncodingException { SecretKey secret = generateKey(); Cipher cipher = Cipher.getInstance( AES/ECB/PKCS5Padding ); cipher.init(1, secret); return cipher.doFinal(message.getBytes( UTF-8 )); } public static String decryptMsg(byte[] cipherText) throws NoSuchPaddingException, NoSuchAlgorithmException, InvalidKeyException, BadPaddingException, IllegalBlockSizeException, UnsupportedEncodingException { SecretKey secret = generateKey(); Cipher cipher = Cipher.getInstance( AES/ECB/PKCS5Padding ); cipher.init(2, secret); return new String(cipher.doFinal(cipherText), UTF-8 ); } } From the preceding code, we can see that the application seems to be performing Advanced Encryption Standard ( AES ) encryption on the data before saving it on the device.

The encryption is a symmetric encryption, which uses the same key to encrypt and decrypt the data.

The key is also a part of the decompiled source code.

That s a security issue – hardcoding the encryption/decryption key in the application code itself.

The key is mentioned in the following line: public static final String password = qkjll5@2md3gs5Q@ ; There are several different types of vulnerability that can be discovered by analyzing the reverse engineered code.

For example, you can find arbitrary code execution if a section of application code allows code from other apps to run.

This type of issue could be discovered by reverse engineering the application and analyzing its code.

So far, we have been working on a debug release of the application.

A debug release does not always contain all the security controls that the release build of the application has.

One of the most important things missing in the debug release is often code obfuscation.

Modifying and recompiling the application Often, it is necessary to not just reverse engineer the application, but also change something, and then repack it.

To create a modified APK, you will need to recompile the modified code and then sign the APK again.

Let s say we want to modify the encryption key in the application and then recompile it.

To do so, you will need to perform the following steps: Decompile the APK.

We have already decompiled the SecureStorage application using apktool , with the #apktool d app-debug.apk command.

The decompilation process will provide us with the required smali files.

So, let s open the EncryptionUtils.smali file.

In this smali file, we can change the value of the encryption key to something else, such as abcdef12345.

To recompile the application, we can again use apktool.

Run the #apktool b command.

Ensure that this command runs in the same directory where the application was extracted.

It will compile the new APK inside the dist folder.

Important Note To install this modified APK on a device, we will need to sign in with a key.

You can generate a key using the keytool tool and then use jarsigner to sign the application again.

Making smaller changes, such as modifying strings or changing a few static elements of the application, is easier and can be done simply by following the preceding steps.

However, to recompile the application after big changes in the smali code, you will need to follow some more recommendations.

Code obfuscation in Android apps Code obfuscation is a process of modifying the code to protect intellectual property and to make it difficult to reverse engineer.

Code obfuscation only modifies the method instructions or metadata; it does not change the logic/flow or the output of the code operation.

Android malware is also known to utilize obfuscation techniques to hide its malicious behavior.

However, obfuscation can also be defeated.

A skilled reverse engineer would be able to defy the obfuscation techniques implemented and still find the interesting bits in the application code.

Developers may use the default obfuscation tool ProGuard , available in Android Studio, or also use a third-party obfuscation tool available in the market.

Depending upon the type of obfuscation used, the de-obfuscation technique should be changed.

ProGuard is an open source command-line tool that can be used to obfuscate Java code.

One of the ways to de-obfuscate the DEX bytecode is by identifying and using the de-obfuscation methods in the application.

This can be done by running the Java code of de-obfuscation methods (the de-obfuscation method code implemented) on the other classes that you want to de-obfuscate.

To understand better, download the release build of the SecureStorage application from the following link: SecureStorage (Release Build): https://github.com/0ctac0der/SecureStorage-AndroidApp/releases/download/1.0/app-release.apk.

This release build has a basic level of obfuscation implemented on it using ProGuard.

Let s decompile it using JADX.

Follow the same steps as followed in the Extracting the Java source code section.

Figure 3.17 – ProGuard obfuscation You can see that the class names have been modified to random letters.

On further analysis, you will notice that the utils section no longer seems to have classes other than CommonUtils.

But, for the app to function, the encryption class and the key have to be there in the code itself.

It is possible to further explore the reverse engineered source code to find the correct place where the EncryptionUtils class is: Figure 3.18 – Obfuscated code of the encryption class We can note that the encryption key being used in the application is still the same, even after the code has been obfuscated.

This is because obfuscation is performed in such a way that the functioning of the application is not changed at all.

The preceding obfuscated code is a result of ProGuard obfuscation, based on the following rule: # class: #-keepclassmembers class fqcn.of.javascript.interface.for.webview { # public *; #} # Uncomment this to preserve the line number information for # debugging stack traces.

#-keepattributes SourceFile,LineNumberTable # If you keep the line number information, uncomment this to # hide the original source file name.

#-renamesourcefileattribute SourceFile -keep class com.example.securestorage.utils.CommonUtils { *; } The ProGuard rule states that com.example.securestorage.utils.CommonUtils should be kept as it is, and the rest of the application code should be obfuscated.

This is exactly what you see in the JADX decompiled code for the release build of the application.

While performing penetration testing, it is not always necessary to de-obfuscate the whole code.

Often, you will only need to understand the code logic, or just de-obfuscate some part of the code.

There are also de-obfuscation tools available, which sometimes can be useful if you are really stuck with some part of the application code, although I would like to recommend a manual analysis of the code to understand it better; only use a de-obfuscation tool as the last resort.

Summary This chapter explained how Android applications are developed, compiled, and packed.

We learned how to perform reverse engineering on Android applications to create the original Java source code.

Once the Java source code is decompiled from the APK, we learned what to look for in the app and how to find security issues.

Obfuscation and de-obfuscation are also important parts of reverse engineering, and we learned how a developer may implement some basic ProGuard obfuscation on the application code before creating the release build.

However, it is not always required that the whole decompiled application code is de-obfuscated as well.

In the next chapter, we are going to have a closer look at reverse engineering an iOS application.

We will explore the tools used for that and will also learn how to enumerate interesting bits in the decompiled application binary of an iOS application..

