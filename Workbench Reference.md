```ps1
function gssh {
    param(
        [string]$Instance,
        [string]$Project,
        [string]$Zone = "europe-west1-b",
        [int[]]$Ports
    )

    $cmd = @(
        "compute", "ssh",
        $Instance,
        "--project", $Project,
        "--zone", $Zone,
        "--tunnel-through-iap"
    )

    foreach ($port in $Ports) {
        $cmd += "--ssh-flag=-L"
        $cmd += "--ssh-flag=$($port):localhost:$($port)"
    }

    gcloud @cmd
}

function sshme { gssh "vineet-k-instance" "project-id" -Ports $args }
function sshjp { gssh "jp-instace" "project-id" -Ports $args }
function sshptv {gssh "pruthvi-hr-instance" "project-id" -Ports $args}
```

Usage
```ps1
sshme 5173
sshjp
sshptv 5173 8080
```

```ps1
PS C:\Users\KushwahaV2> gcloud compute scp `
>>     C:\Users\KushwahaV2\Downloads\test.txt `
>>     vineet-k-instance:~/test.txt `
>>     --project project-id `
>>     --zone europe-west1-b `
>>     --tunnel-through-iap
FATAL ERROR: Remote side unexpectedly closed network connection
ERROR: (gcloud.compute.scp) [C:\Program Files\Google\google-cloud-sdk\bin\sdk\pscp.exe] exited with return code [1].
```