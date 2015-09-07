#FSND Catalog App - P3


###Author
Rick Ertl
https://github.com/rickertl


###App Features
* Provides a list of items within a variety of categories
* Integrates third party Google Plus and Facebook OAuth user registration
  and authentication
* Authenticated users have the ability to post, edit, and delete their
  own items
* JSON and XML API endpoints for categories and category items
* Image upload capability available per item


###Setup
1. Start with any local operating system such as Mac OS X, Linux, or Windows
2. Install VirtualBox
3. Install Vagrant
4. Clone or extract FSND-catalog project into a local directory (i.e., catalog)
   git clone git://github.com/rickertl/FSND_catalog catalog
   OR download and extract the repository master zip file to a catalog
   directory on your computer
5. In a command prompt, change into the new directory with 'cd catalog'
6. Start the Vagrant environment with 'vagrant up'
7. Once Vagrant is up and running, type 'vagrant ssh' to log into it. This
   will log your terminal in to the virtual machine, and you'll get a
   Linux shell prompt. When you want to log out, type 'exit' at the shell
   prompt. To turn the virtual machine off (without deleting anything),
   type 'vagrant halt'.
8. At terminal prompt, type 'cd /vagrant' to switch into VM app directory
9. For sqlite DB to be created with proper data structure, type
   'python database_setup.py' into the Terminal
10. For dummy data to populate database, type 'python duck_data.py' into the
    Terminal


###Start up
1. Once setup complete, run application within the VM by typing ​'python
   /vagrant/catalog/application.py' into the Terminal
2. Navigate to http://0.0.0.0:5000/ with your browser
   (note: Mac OSX Safari currently is having issue with HTML 5 video rendering)


###Credits
• Python
• Flask
• JQuery
• Bootstrap front-end framework
• Google Fonts
• Shutterstock - for homepage video
• https://github.com/callmenick/Full-Screen-Background-Video

