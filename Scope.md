- [x] UI: a progress bar for ongoing progress

- [x] UI: colors to 
```bash
Planned changes:
  • 1 to add
  • 7 to modify
  • 1 to delete
```
- [] Fix: output diff priting intendation

- [] Feat: Allow variablizing of commonly used endpoints

- [] Feat: -c / -clean flag to clean the .relay.db once the job is done since not all src/dst require the db to exist.

- [] Fix: Streamline the resolution of ignores, establishing a proper ignore list, command specific ignore for files/dirs. Day-to-day workflow doesn't make sense to have node_modules (helps with network bandwidth) but some requirements may have things like node_modules

- [] Feat: In reference to the previous fix - I think it would be a better idea to zip and unzip directories with large number of children, because frankly anybody would hate the 3000 file transfers on a single command.

- [] Feat: Recognize copy creation from sync - if directory doesn't exist by default it is created but we should have maybe a "no files found" => new copy + create directory => ask user (or read flag)