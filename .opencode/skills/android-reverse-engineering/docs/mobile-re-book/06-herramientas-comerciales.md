# Herramientas Open Source y Comerciales

B17428_06_ePub Chapter 6 : Open Source and Commercial Reverse Engineering Tools In the chapters so far, we have discussed reverse engineering iOS and Android applications.

We mainly used open source tools, with one exception – Hopper Disassembler.

Once you start reverse engineering real-world mobile applications, on both Android and iOS, you might find some alternative tools as well.

Those alternatives can also be open source or commercial (closed source).

All the open source tools we have used so far, such as APKTool, Ghidra, and Radare2, are all free to use, and the closed source one, Hopper Disassembler , is commercially available.

So, for the remaining part of the chapter, let s consider what we mean by closed source when we are talking about commercially available tools.

Different reverse engineering tools offer different (and unique) features.

It also often becomes a personal choice of which tool you want to use, and for what purpose.

For example, I prefer using Hopper Disassembler for all iOS binary reverse engineering over Ghidra.

This is primarily because I feel more comfortable working with Hopper than Ghidra.

Another reason for someone to prefer Radare2 over Ghidra could be that they like working on a command-line interface rather than a graphical user interface, or the visual mode of Radare2 looks cleaner than having all the disassembled code in one window.

There is a lot of similarity between the features and support that these tools offer, but there are crucial differences, which might make one tool more suitable for a particular job over another.

To help you understand the pros and cons of one tool over another, in this chapter, we will be covering the following topics: Some common open source tools for reverse engineering Some common commercial (closed source) tools for reverse engineering A case study for reverse engineering and the required capabilities of a reverse engineering tool Technical requirements We will be using the Ubuntu virtual machine setup that we used in the previous chapter.

This chapter does not have any additional technical requirements.

Tools for mobile application reverse engineering There are several options when it comes to choosing a reverse engineering tool for mobile applications.

Mobile applications have dex or Mach-O (OS-x) binary files, which are generally the prime focus during reverse engineering.

A tool that supports mobile device architectures and can decompile, disassemble, and patch a mobile application would be the right choice of tool for penetration testing.

However, sometimes, there are more complex problems that need to be solved, some advance obfuscation performed, and external library files also need to be reverse engineered.

In such cases, the reverse engineering tool would need to have these advanced capabilities.

Let s have a look at some of the commonly used open source and commercially available reverse engineering tools, which can be used for mobile applications.

Open source mobile application reverse engineering tools Open source tools have their source code publicly available for others to inspect, modify, and enhance.

The following list gives information on some of the common open source tools used for reverse engineering: Ghidra : Probably the most common and advanced open source and free reverse engineering tool used for mobile application reverse engineering.

Some of the key capabilities of Ghidra include assembly, disassembly, and decompilation.

Ghidra supports a wide variety of processor instruction sets and executable formats.

The official GitHub repository can be found here: https://github.com/NationalSecurityAgency/ghidra.

The Radare2 framework : A multi-architecture and multi-platform tool, capable of assembling and disassembling executables, which it can also perform binary diffing with graphs and extract information.

A more detailed capability list can be found on the official Radare2 page: https://www.radare.org/r/.

The official GitHub repository can be found here: https://github.com/radareorg/radare2.

JADX (only for Android apps) : Unlike the iOS binary, it is comparatively easier to reverse engineer Android apps.

This is mainly because the dex file can easily be converted to Java code.

One of the most common tools used for this purpose is JADX.

This is basically a Java decompiler; it can decompile Dalvik bytecode to Java classes from APK, dex , aar , aab , and more.

The official GitHub repository can be found here: https://github.com/skylot/jadx.

Next, let s look at commercial tools.

Commercial mobile application reverse engineering tools There are a lot of very useful and advanced reverse engineering tools available as commercial tools.

These are generally closed source and have different licensing models.

Let s have a look at some of the famous, commercial reverse engineering tools.

The following list gives information about some of the commonly used closed source tools for reverse engineering: Hopper : A reverse engineering tool to disassemble, decompile, and debug iOS (ARM) executables (and multiple other executables/binaries as well).

Hopper Disassembler comes in a free version as well, with a time restriction of usage.

At the time of writing this chapter, a personal license can be purchased from the official website, at a cost of $99–$129, depending upon the time of the licensing model you chose.

Having a cheaper and personal license makes this tool very popular among mobile application penetration testers.

The official website can be found here: https://www.hopperapp.com/ IDA : A widely used reverse engineering tool, with the capabilities of a disassembler and a debugger.

The professional version (IDA PRO) is one of the most advanced and capable reverse engineering tools available.

There are some other versions of IDA available, such as IDA Home and IDA Free.

The main difference between IDA Pro and IDA Home is in supported processors and debuggers.

A detailed list of differences between all the versions of IDA can be found on the official website: https://hex-rays.com/ida-pro/#main-differences-between-ida-editions.

IDA Free is a binary code analysis tool with some basic IDA functionalities.

IDA comes in three types of licenses – named license, computer license, and floating license.

More details on IDA license types can be found here: https://hex-rays.com/licenses/.

The price details of all IDA tools and licenses can also be found on the official website: https://hex-rays.com/cgi-bin/quote.cgi/products.

IDA Pro supports a huge number of processor types and binary formats but comes with a costly license model.

This makes it more preferable for advanced reverse engineering needs.

The official website can be found here: https://hex-rays.com/ida-pro/.

Binary Ninja : An interactive disassembler, decompiler, and binary analysis platform.

This is another very popular tool among penetration testers and reverse engineers.

It also comes with a demo/trial version, with limitations.

The license is available for personal (non-commercial), commercial, and enterprise.

More details about the pricing can be found here: https://binary.ninja/purchase/.

The license cost of Binary Ninja sits between Hopper Disassembler and IDA.

The official website can be found here: https://binary.ninja/.

JEB Decompiler : A reverse engineering platform to perform disassembly, decompilation, debugging, and analysis of code and document files, manually or as part of an analysis pipeline.

JEB Decompiler also comes in a community version that can be used for non-commercial use.

The license comes in three types – JEB Android, JEB Pro, and JEB Floating.

More details about the pricing can be found at https://www.pnfsoftware.com/jeb/buy.

The official website can be found here: https://www.pnfsoftware.com/.

Important Note The preceding list of open source and commercial reverse engineering tools is not an exhaustive list.

These are just the most commonly used and famous reverse engineering tools available.

When it comes to reverse engineering of mobile applications, the choice of tool depends majorly on the following factors: The type of mobile application to be reverse engineered – iOS, Android, or both.

What is the purpose of reverse engineering? This can be for any of the following reasons: Bypassing one or more security controls in the application Understanding logic behind some specific part of the application Finding security issues in the application related to code quality, the security controls implemented, and so on.

Analyzing strings and static content stored inside the application package and application binary Exploit writing Is it required to patch the binary and create the app with modified code? We now know about the commonly used open source and commercial reverse engineering tools.

Let s also understand the capabilities required from these tools during a penetration test.

Case study – reverse engineering during a penetration test One of the primary reasons for reverse engineering a mobile application during a penetration test is to analyze whether the source code has any sensitive information hardcoded, which can further be used by a malicious actor.

Other reasons might be bypassing security controls such as SSL pinning, root/jailbreak detection, and role-based client-side access control.

However, depending on the type of application and pentest, you might have to spend more effort in performing a more in-depth analysis of a reverse engineered application.

Let s look at one of the case studies.

During the penetration test of a FinTech application, it was noticed that the application sent some critical requests to uniquely generated URL endpoints.

These endpoints were unique for every request, and in fact, they were getting generated right before the HTTP(s) request was generated.

In order to find the way this application generates these URLs, we could do one of the following: Reverse engineer the application to find the logic (or function) of how these URLs are generated.

Perform runtime instrumentation to analyze the application while it is running.

In this method, we inject a piece of code inside the running process of the application and then analyze its behavior.

One of the commonly used tools to perform runtime instrumentation is Frida ( https://frida.re/ ).

On disassembling the application binary and analyzing the logical flow during that specific step, it was revealed that the application creates an SHA-256 hash of the user s ID and session ID.

This hash is then used as a part of the URL, such as the following: User ID: 53e726ce-954f-4291-9968-063521b87483 Session ID: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3JfMTIzIiwiaWF0IjoxNDU4Nzg1Nzk2LCJleHAiOjE0NTg4NzIxOTZ9.-LzT9cobGUNslZ4JSELQFwSxp5JpT5o6KtMO8ySR-20 SHA-256 hash: FFDC52D453CF836BAC761D7463B85A7AB6EF4DB 511366A27684734E7154C461A Final unique URL: https://[RedactedDomainName]/user/admin/escalate/ FFDC52D453CF836BAC761D7463B85A7AB6EF4DB511366A 27684734E7154C461A Final HTTP(s) request: POST /user/admin/escalate/ FFDC52D453CF836BAC761D 7463B85A7AB6EF4DB511366A27684734E7154C461A HTTP/1.1 Host: ://[RedactedDomainName] Cookie: session= eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3JfMTIzIiwiaWF0IjoxNDU4Nzg1Nzk2LCJleHAiOjE0NTg4NzIxOTZ9.-LzT9cobGUNslZ4JSELQFwSxp5JpT5o6KtMO8ySR-20 User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:96.0) Gecko/20100101 Firefox/96.0 Accept: application/json Accept-Language: en-US,en;q=0.5 Accept-Encoding: gzip, deflate Content-Type: application/x-www-form-urlencoded; charset=UTF-8 X-Requested-With: XMLHttpRequest Content-Length: 276 Sec-Fetch-Dest: empty Sec-Fetch-Mode: cors Sec-Fetch-Site: same-origin Te: trailers Connection: close p_web_site_id=3982358328326 p_language=EN p_show_form_in_div=N p_format=HTML p_print=JSONP p_joblocation=WWW p_current_host=gdx9tof61hm58kkaz4k0dp3qnht8hx Important Note The SHA-256 hash is created from the id=53e726ce-954f-4291-9968-063521b87483; sessionId=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3JfMTIzIiwiaWF0IjoxNDU4Nzg1Nzk2LCJleHAiOjE0NTg4NzIxOTZ9.-LzT9cobGUNslZ4JSELQFwSxp5JpT5o6KtMO8ySR-20 string.

You can use any hash creator tool to create this hash.

The previous implementation suggests that it was intended to hide the actual URL and only allow the request with a valid hash to access the endpoint.

The hash is also calculated on the application server and matched with the hash in the request, and then internally redirected to the correct URL.

Once it was confirmed that the actual URL is rather static, a content discovery fuzzing of the endpoint was done.

This revealed that the internal URL was in fact exposed publicly also.

Here, an assumption was made by the developer as well as the DevOps team that no one will be communicating with the actual URL, and hence, no one really validated whether the actual URL was accessible directly or not.

Solving a challenge such as this requires good disassembling, search, and de-obfuscation features in a reverse engineering tool.

Open source tools such as Ghidra and Radare2 can very well be used to solve this.

The reverse engineering capabilities required during a penetration test might differ from that during malware analysis.

In a penetration test, reverse engineering is generally done to solve a piece of a puzzle or to explore some functionality.

However, during malware analysis, reverse engineering is done to explore every piece of an application and understand all hidden features and code.

Let s have a look at a malware analysis case study.

Case study – reverse engineering during malware analysis Another field of work that requires more advanced reverse engineering skills is malware analysis.

Malware researchers spend days and weeks looking at disassembled and decompiled binaries to deduce the application flow.

Let s take another case study.

During the analysis of a malware mobile app, it was noticed that the application somehow modifies its behavior depending on factors such as country, language, and applications installed.

For a device in the United States, with the English language, and that had financial/banking apps, the application would try to read messages and the transaction history.

However, on a different device in a different country, and with dating apps installed, it would try to inject ads in the traffic of other apps.

Such a change in behavior cannot be noticed if the application is only used on one device.

However, a good analysis of the disassembled application binary and its associated libraries revealed this behavior of the application.

During this analysis, IDA Pro was used for its features such as reference search, populating current code states to a database, and pseudo code.

Other tools, such as Binary ninja, can also provide some of these features.

In this case, basic disassembling and search features might not be enough, and hence, we might have to choose a more advanced and capable reverse engineering tool.

Also note that, in this case, the associated library files were also reverse engineered.

There are numerous such cases when a more advanced feature is required in a reverse engineering tool or the tools need to support different types of architectures.

Interface choice is also a big reason why some might prefer one tool over another.

Summary This chapter talked about some commonly used open source and commercial reverse engineering tools.

We also discussed some case studies to understand what type of features and capabilities would be required in a tool to solve the problem.

For the majority of tasks done during a penetration test, basic disassembling and debugging are needed, so an open source reverse engineering tool would be enough for such a requirement.

However, for more advanced features and capabilities, we would have to go with a commercial reverse engineering tool such as IDA Pro or Hopper.

It is also important to feel comfortable with the graphical interface (or visual mode) that each of these tools have.

That s another reason why someone prefers one reverse engineering tool over another.

For the reverse engineering of mobile applications, the important features/capabilities that the tools must have are the disassembly and assembly of OSx and dex files, decompilation, graphing, patching of the binary files, and string search.

Tools such as Ghidra and Radare2 can very well perform the aforementioned tasks.

Another important point is that the Android application binaries can be reverse engineered easily, in comparison to the iOS application binary.

This is basically because the dex files can be converted to Java code, using a decompiler such as JADX.

In the next chapter, we will look at some of the ways we can use automated scanners, which can also perform a bit of reverse engineering.

This might be useful when you have a huge list of applications to reverse engineer and only want to find some basic things in those apps – for example, I am looking for a specific string in a hundred different applications, or I am interested in only checking for some binary protections on hundreds of mobile app binaries.

Such tests can be easily automated using open source tools.

We will look more closely into this in the next chapter..

