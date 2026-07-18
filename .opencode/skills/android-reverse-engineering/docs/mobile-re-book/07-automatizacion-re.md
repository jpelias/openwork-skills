# Automatización del Proceso de RE

B17428_07_ePub Chapter 7 : Automating the Reverse Engineering Process During a penetration test or malware analysis, reverse engineering is generally performed on one binary (or application) at a time because the aim of reverse engineering is to analyze a single application.

However, there can be cases when you need to quickly analyze a lot of applications for some generic details.

For example, you want to find out whether a specific method is being used in any of the applications you are working on, or you want to find out whether a specific string (or strings) is a part of any of the available application binaries.

In such cases, it would be really helpful if you could automate these tasks.

A static analysis is often the very first step during a black box penetration test of a mobile application.

The static analysis helps to quickly analyze the application based on the reverse engineered code, extract strings, analyze the binary for some basic protections, and can also perform a quick malware analysis.

So, let s have a look at how we can automate some part of the static reverse engineering using open source tools as well as some scripting.

In this chapter, we will be covering the following topics: Using an open source tool to automatically perform a static analysis of Android and iOS applications Understanding a case study to automate a few reverse engineering tasks Writing scripts to automatically perform a few tasks on binaries Technical requirements We will be using the Ubuntu virtual machine setup, which we used in the previous chapter.

In this chapter, we will be using Docker inside the Ubuntu virtual machine to run Mobile Security Framework.

Automated static analysis of mobile applications The first step during a black box penetration test is to gather as much information as possible about the target.

In the case of a mobile application penetration test (black box), a static analysis of the application package ( Android Application Package ( APK ) or iOS application archive ( IPA )) is done to get a basic idea about the application, as well as to analyze it for some low-hanging vulnerabilities and missing security controls.

Let s have a look at things that a static analysis tool can check on an application: Extract details about the application from the application s manifest (for Android) or PLIST (for iOS) files.

Analyze the binary for protections such as Automatic Reference Counting ( ARC ), code signing, and Position Independent Executable ( PIE ).

Important Note ARC is used for automatic memory management in iOS apps.

This is done by handling the reference count of objects at the time of compilation.

The PIE flag is used in iOS application binaries to protect against Address Space Layout Randomization ( ASLR ) by randomizing the application object s location in the memory for every application restart.

Reverse engineer the application binary to extract Java code (for Android apps), classes (for iOS apps), strings, and so on Analyze the binary for the use of insecure APIs.

These are some of the initial test cases to be performed, and a lot of this can be done by analyzing the reverse engineered binary.

The most famous tool used for static analysis of mobile applications is Mobile Security Framework ( MobSF ).

Let s set up MobSF and perform automated reverse engineering on SecureStorage iOS and Android applications.

MobSF MobSF is an open source security assessment framework for mobile applications.

It supports mobile app binaries (APK, XAPK, IPA, and APPX) along with zipped source.

We are going to have a look at the use of MobSF in quickly reverse engineering and analyzing the reverse engineered binaries.

The MobSF GitHub repository can be found here: https://github.com/MobSF/Mobile-Security-Framework-MobSF.

Setting up MobSF As per the official documentation, we can set up this tool on a Linux virtual machine either by cloning the repository and then running the setup.sh file or using a Docker container.

Important Note MobSF requires Xcode command-line tools for IPA analysis, which can only work on Mac, Linux, and Docker containers.

Let s set up MobSF using the Docker container and analyze the SecureStorage application.

To do so, we first need to install Docker on our Ubuntu virtual machine.

The steps to do so can be found on the official Docker website: https://docs.Docker.com/engine/install/ubuntu/.

To install Docker Engine, you can follow these steps: To set up the repository, use the following code: # sudo apt-get update # sudo apt-get install \ ca-certificates \ curl \ gnupg \ lsb-release Next, add Docker s GPG key: # curl -fsSL https://download.Docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg Set up the stable repository: # echo \ deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \ $(lsb_release -cs) stable | sudo tee /etc/apt/sources.list.d/docker.list /dev/null Update the apt package index: # sudo apt-get update Install Docker Engine: # sudo apt-get install docker-ce docker-ce-cli containerd.io Once Docker Engine has been installed, you can verify whether it s running properly by using the following command: # sudo docker run hello-world The following screenshot shows the output of the preceding command: Figure 7.1 – Running the hello-world container on Docker Once we have the container ready, we can now download a prebuilt Docker container and run it directly.

Running the MobSF Docker container A prebuilt Docker container can be found on Docker Hub.

To download and run the container, use the following code: Downloading the container from Docker Hub: # sudo docker pull opensecurity/mobile-security-framework-mobsf Here s the output: Figure 7.2 – Downloading the MobSF container Run the following on the container on port 8000 : # sudo docker run -it --rm -p 8000:8000 opensecurity/mobilesecurity-framework-mobsf:latest The output is shown in the following screenshot: Figure 7.3 – Running the MobSF container Once this is done, you should be able to access the MobSF dashboard at http:127.0.0.1:8000.

Figure 7.4 – The MobSF dashboard Now that we have the MobSF tool running, we can perform a static analysis of iOS and Android apps.

Performing a static scan on SecureStorage Once we have MobSF running, simply drag and drop IPA or APK to complete the static analysis.

Once the scan is complete, you will be presented with a report.

Static analysis of APK During a static analysis of APK, MobSF performs the following tasks: Decompiling and extracting content such as hardcoded certificates/key stores Converting AXML to XML Extracting and analyzing manifest data Creating the Java code Converting DEX to SMALI Extracting strings As you can see, a lot of these tasks are the same as the ones we performed during our manual reverse engineering of the Android application.

Once the analysis is done, we can use the MobSF dashboard to download the reverse engineered JAVA code, strings, AndroidManifest file, and more for a manual analysis.

MobSF also performs an automated analysis of the extracted content and provides us with a report containing all the information (including any security issues discovered).

Static analysis of IPA During the IPA analysis, MobSF performs the following tasks: Extracting the IPA Analyzing the Info.plist file A Mach-O analysis of the binary Dumping classes from the binary Binary analysis Once the analysis is done, we can download the reverse engineered entities, such as strings , classdump , and Info.plist.

MobSF also performs a quick check on the binary for some protections.

Figure 7.5 – IPA binary analysis Note that this is the same information that we collected during the manual reverse engineering of the SecureStorage binary using Radare2 in Chapter 5 , Reverse Engineering an iOS Application (Developed Using Swift).

The REST APIs in MobSF can also be used to further automate the process of static analysis of the applications.

Using MobSF, we have automated some part of the basic reverse engineering that we did manually in Chapter 3 , Reverse Engineering an Android Application , and Chapter 4 , Reverse Engineering an iOS Application.

However, this is in no way an alternative to a deep manual analysis of the reverse engineered binary implemented during a penetration test or malware analysis.

However, using a tool such as MobSF can be extremely helpful while performing an analysis of a large number ( 5) of applications in a quick timeframe.

The automation reduces the overhead time.

Let s understand this using a case study.

Case study one – automating reverse engineering tasks During a research project, we need to analyze how secure modern mobile applications are and what percentage of these applications do not follow some best security practices of binary protection, such as a stack canary and a PIE flag.

In order to complete such research on a wide range of IPAs, we would need to automate the process of binary analysis and reverse engineering.

This is where using a tool such as MobSF can be very productive.

Here is how we performed such checks on more than 500 applications: We stored all IPAs at one location.

We then used the MobSF REST APIs to automate the static analysis of binaries one by one: By uploading the file: api/v1/upload By scanning the uploaded file: /api/v1/scan Once the analysis is done, a JSON format of the report could be fetched and analyzed to find the value of checks we are interested in: By generating the JSON report: api/v1/report_json We then grepped the JSON report for our interesting values.

Figure 7.6 – Extracting the JSON report Once we have the report in JSON format, we can quickly hunt for specific data that we are looking for, such as the status of binary protection.

There can be a lot of other scenarios where you might need to perform some part of reverse engineering on a huge number of applications (or binaries).

If the test case falls under the list of automated scanners such as MobSF, then you can use it.

However, sometimes, the test case is very specific, and you can t run a static scan and compare reports.

Case study two – automating test cases to find security issues During an audit, we noticed that all mobile applications developed by a specific team used a list of common secrets and hardcoded values in the code.

As it was also a black box penetration test, we did not have any source code but had a list of 10+ Android applications to test.

We wanted to find out how many of these applications have the same secrets and hardcoded accounts inside the application code.

One way of doing this could have been by manually extracting strings from each of these application binaries and then searching for them.

But we automated this part a little bit by following these steps: Extracting all dex files from the APKs, using the unzip utility Running strings on all dex files and saving the result in different text files Grepping through all the text files containing strings to search for our specific strings A simple script to automate this would look like this: #!/bin/bash #For all files in the directory (all APKs are in this directory): for file in *.apk do echo Extracting $file #Printing the name of file mkdir classes.

$file #Creating a directory with app name unzip $file -d classes.

$file / *.dex #extracting the content of APK in temp directory #mv temp/classes* classes.$file #Moving all dex files to the new directory #Running string on each dex file and saving the output to a single strings.txt file find classes.

$file / -iname *.dex -exec strings {} classes.

$file /strings.txt \; done Important Note The preceding script might also create directories with the names classes.run.sh ( run.sh is the bash script in the same directory) and classes.temp ( temp is the folder being created).

To remove these directories, add the following two lines in the bash script: rm -rf classes.run.sh rm -rf classes.temp The preceding script will automate the process of extracting dex files from a group of APKs and will then extract strings from all dex files from the same APK and save them in the strings.txt file (in each APK directory).

Once we have the strings for all APKs, the bash script can be extended to search for a specific string in those sets of strings.txt files.

This is another case study of how you can automate some part of the reverse engineering process using a custom bash script.

Summary This chapter talked about some case studies and gave some examples when automating the reverse engineering process that might be helpful.

Remember that reverse engineering can be extremely in depth depending on what you are trying to achieve with it.

Finding hardcoded strings, class names, and more are the simpler tasks done through reverse engineering.

However, there can be a lot of complex challenges for which an in-depth, manual analysis and reverse engineering might be required.

Automating all such requirements is not always possible.

But it is usually a good idea to automate the part of your work that you will need to perform again and again – for example, extracting strings and classes from mobile application binaries.

That s it for this chapter.

In the next and final chapter of this book, we will summarize what we have discussed, what more can be explored in order to enhance your knowledge, and what should be the way ahead..

