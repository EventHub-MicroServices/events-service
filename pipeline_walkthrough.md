# 🚀 CI/CD Pipeline Architecture: A Beginner's Guide

Welcome! If you're new to CI/CD (Continuous Integration / Continuous Deployment) or to GitHub Actions, this guide will walk you through exactly how our repository pipelines are built, why they are designed this way, and how the different puzzle pieces fit together.

---

## 1. The High-Level Goal

Whenever a developer pushes code to the repository, we need to guarantee two things automatically:
1. **The code is safe, clean, and has no critical vulnerabilities.**
2. **If it passes our checks, it gets safely bundled into a Docker container and delivered to Docker Hub.**

To achieve this natively inside GitHub, we use **GitHub Actions**. Our logic lives inside `.github/workflows/`.

---

## 2. Our Two Primary Workflows

We split our pipeline into two specific workflows:

### 🛡️ The CI Workflow (`ci.yaml`)
This is our "Gatekeeper." It automatically runs on every push and pull request. 
- Analyzes our raw source code for bugs and bad coding practices using **SonarQube**.
- Scans our code's third-party dependencies for known vulnerabilities using **Snyk**.
- *If any critical vulnerabilities or bugs are found, this pipeline fails and blocks the code from moving forward.*

### 🐳 The Docker Workflow (`docker.yaml`)
This is our "Deliverer." 
- It uses a native feature called `workflow_dispatch`, meaning it waits for us to manually trigger it and provide an exact version tag (like `v1.2.0`).
- It builds the code into a container, does a final scan on that generated container using **Trivy**, and (if it passes) pushes it securely to our Docker registry so it can be deployed.

> [!TIP]
> **Why separate them?** We want to run fast security tests constantly on every code change (CI), but we only want to build and deploy Docker images when we purposefully initiate a new release.

---

## 3. The "Unified Single-Job" Strategy

If you open `docker.yaml`, you'll notice all instructions (Build, Scan, Push) live inside one giant job called `docker-pipeline`. 

**Why didn't we split them into three smaller jobs?**

Every time you define a new `job:` in GitHub Actions, GitHub boots up a brand-new, empty Ubuntu virtual machine.
- If we had 3 jobs, GitHub would boot 3 separate Ubuntu machines.
- That means the "Scan" machine wouldn't have the Docker image built by the "Build" machine unless we compressed it, uploaded it, and downloaded it across the internet.
- **The Optimization:** By keeping sequentially dependent tasks inside a single job, they all run on the exact same Ubuntu machine! This avoids the "boot-up tax" (saving 10-20 seconds per step) and completely eradicates the need to zip, upload, and download heavy files between jobs, saving minutes and cutting cloud compute costs!

---

## 4. Deep Dive: The Magic of Composite Actions

You might notice that whenever a job finishes—whether successfully or with an explosion of failure—the workflow file suddenly calls `uses: ./.github/actions/slack-notify`. 

This is a **Composite Action**. Since you will be writing and modifying these pipelines, understanding how this works is critical!

### What is a Composite Action?
In basic programming, if you find yourself copying and pasting the same 30 lines of code across different files, you wrap them inside a "function." You then just execute that function, passing in different variables when you need it. 

A Composite Action is exactly that: **a function for GitHub Actions**. It allows you to package standard GitHub Actions steps inside their own folder so you can reuse them anywhere in your repository without duplicating code.

### 1. Defining the Function (`inputs`)
Open `.github/actions/slack-notify/action.yaml`. At the very top, you will see an `inputs:` block. This defines the arguments our function accepts.

```yaml
# Inside action.yaml
inputs:
  status:
    required: true
    description: "'success' | 'failed'"
  pipeline:
    required: true
  job_name:
    required: true
  error_message:
    required: false
    default: "Check the GitHub Actions run for details."
```
Think of these as empty placeholders. The action waits for the main workflow to inject data into these variables. Once injected, the action can access them anywhere using `${{ inputs.status }}`.

### 2. Processing the Data (Internal `$GITHUB_OUTPUT`)
Once the action has the inputs, it needs to process them. Inside our composite action, the first step is a Bash script called `Resolve notification context`. 

If it sees the input was `"success"`, it needs to prepare a green color and a checkmark emoji. But **GitHub Action steps cannot natively share variables with each other unless you specifically output them.**

Here is how we set an internal output variable in Bash:
```bash
# Inside the Bash script step (id: ctx) in action.yaml
if [ "${{ inputs.status }}" = "success" ]; then
  echo "status_emoji=✅" >> $GITHUB_OUTPUT
  echo "color=#2EB67D"   >> $GITHUB_OUTPUT
fi
```
Later in the action, when we actually send the Slack message, we grab those internal variables using the ID of that exact step (`ctx`):
`"text": "${{ steps.ctx.outputs.status_emoji }} PIPELINE SUCCEEDED"`

### 3. Calling the Action from a Workflow (`with`)
Now, how do you actually use this when you are writing a new pipeline?

Instead of writing 150 lines of Slack formatting, you just write 5 lines. You use the `uses` keyword to point to the folder path, and the `with` keyword to map your current pipeline data into those `inputs` we defined earlier!

```yaml
# Inside YOUR workflow file (e.g., ci.yaml or docker.yaml)
      - name: Trigger Notification
        uses: ./.github/actions/slack-notify
        with:
          status: "failed"
          pipeline: "Docker"
          job_name: "docker-build"
          
          # We can even dynamically pass the exact error message!
          error_message: ${{ steps.capture-build-error.outputs.error_msg }}
          
          # Don't forget your secure secrets!
          slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**How it all connects:** 
When the runner reaches this step, it takes your `with` values and aggressively dumps them into the action's `inputs`. The composite action boots up, processes the strings via the Bash `$GITHUB_OUTPUT`, injects them into the raw Slack API JSON, and fires off the notification.

> [!NOTE]
> Because of this `with` block architecture, whenever you create a brand-new workflow in the future, you just have to add those few lines calling the action. The entire heavy lifting of translating emojis, formatting HTML emails, and configuring Slack Webhooks is universally handled for you!

---

## 5. Security & Secrets

How does GitHub safely log into Docker Hub or Google Mail without our passwords being public in the code?

We use **GitHub Secrets** (`${{ secrets.DOCKERHUB_TOKEN }}`). These are securely encrypted vault variables. Even if a teammate reads the pipeline code, they can never see your Gmail App Password—they only see the placeholder variable.

*By combining hardened secrets, single-job speed optimizations, and composite action reusability, our CI/CD pipeline is built to enterprise professional standards!*
