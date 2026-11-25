- [x] 1. UI: a progress bar for ongoing progress

- [x] 2. UI: colors to 
```bash
Planned changes:
  • 1 to add
  • 7 to modify
  • 1 to delete
```
- [] 3. Fix: output diff priting intendation

- [] 4. Feat: Allow variablizing of commonly used endpoints

- [x] 5. Feat: -c / -clean flag to clean the .relay.db once the job is done since not all src/dst require the db to exist.

- [] 6. Fix: Streamline the resolution of ignores, establishing a proper ignore list, command specific ignore for files/dirs. Day-to-day workflow doesn't make sense to have node_modules (helps with network bandwidth) but some requirements may have things like node_modules

- [x] 7. Feat: In reference to the previous fix - I think it would be a better idea to zip and unzip directories with large number of children, because frankly anybody would hate the 3000 file transfers on a single command.

- [] 8. Feat: Recognizing 'new project creation' from 'sync' - if root directory doesn't exist by default it is created but we should have maybe a "no files found" => new copy + create directory => ask user (or read flag)- so as to prevent misfire of paths - also consider compatibility with #5 since just existance of .relay.db cant be considered as a valid bais for new vs exisiting.

- [] 9. Feat: (along with #4) Command history, mainting a global used command history with interactive cli so that user can scroll with down and up key and press enter to run that same command. 