const os = require("os");
const path = require("path");
const fs = require("fs/promises");
const { exec } = require("child_process");
const util = require("util");
const execPromise = util.promisify(exec);

function getBasePath() {
    const re = os.homedir();
    switch (process.platform) {
    case "darwin":
        return path.join(re, "Library/Application Support/CodeBuddyExtension");
    case "win32":
        return path.join(re, "AppData", "Local", "CodeBuddyExtension");
    default:
        return path.join(re, ".local", "share", "CodeBuddyExtension")
    }
}

const OAUTH_FILE = path.join(getBasePath(), "Data/Public/auth/Tencent-Cloud.coding-copilot.info");

class CodeBuddyCLITransformer {
  name = "codebuddy-cli";

  constructor() {
    fs.watch(OAUTH_FILE, () => {
      try {
        this.getOauthCreds();
      } catch {}
    });
  }

  async transformRequestIn(request, provider) {
    if (!this.oauth_creds) {
      await this.getOauthCreds();
    }
    if (this.oauth_creds && this.oauth_creds.auth && this.oauth_creds.auth.expiresAt < +new Date()) {
      await this.refreshToken(this.oauth_creds.auth.refreshToken);
    }

    const headers = {
      "Accept": "application/json",
      "X-Requested-With": "XMLHttpRequest",
      "x-stainless-arch": "arm64",
      "x-stainless-lang": "js",
      "x-stainless-os": "MacOS",
      "x-stainless-package-version": "5.10.1",
      "x-stainless-retry-count": "0",
      "x-stainless-runtime": "node",
      "x-stainless-runtime-version": "v22.12.0",
      "X-Conversation-ID": this.generateUuid(),
      "X-Conversation-Request-ID": this.generateUuid(),
      "X-Conversation-Message-ID": this.generateUuid(),
      "X-Request-ID": this.generateUuid(),
      "X-Agent-Intent": "craft",
      "X-IDE-Type": "CLI",
      "X-IDE-Name": "CLI",
      "X-IDE-Version": "1.0.8",
      "Authorization": `Bearer ${this.oauth_creds.auth.accessToken}`,
      "X-User-Id": this.oauth_creds.account.uid,
      "X-Domain": this.oauth_creds.auth.domain,
      "User-Agent": "CLI/1.0.8 CodeBuddy/1.0.8",
      "X-Product": "SaaS",
      "Host": "www.codebuddy.ai",
      "Connection": "close",
      "Content-Type": "application/json"
    };

    const transformedRequest = {
      model: request.model,
      messages: request.messages,
      tools: request.tools,
      temperature: request.temperature || 1,
      max_tokens: request.max_tokens || 16384,
      response_format: request.response_format || { type: "text" },
      stream: request.stream || false
    };

    return {
      body: transformedRequest,
      config: {
        headers: headers,
      },
    };
  }

  async refreshToken(refresh_token) {
    const urlencoded = new URLSearchParams();
    urlencoded.append("client_id", "console");
    urlencoded.append("refresh_token", refresh_token);
    urlencoded.append("grant_type", "refresh_token");
    return fetch("https://www.codebuddy.ai/auth/realms/copilot/protocol/openid-connect/token", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: urlencoded,
    })
      .then((response) => response.json())
      .then(async (data) => {
        if (data.error) {
          const { stderr } = await execPromise("ls -lh");
          if (!stderr) {
            this.getOauthCreds();
          }
          return;
        }
        data.auth.expiresAt = new Date().getTime() + data.auth.expiresIn * 1000 - 1000 * 60;
        data.auth.refreshToken = refresh_token;
        delete data.auth.expiresIn;
        this.oauth_creds = data;
        await fs.writeFile(OAUTH_FILE, JSON.stringify(data, null, 2));
      });
  }

  async getOauthCreds() {
    try {
      const data = await fs.readFile(OAUTH_FILE);
      this.oauth_creds = JSON.parse(data);
    } catch (e) {}
  }

  generateUuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
}

module.exports = CodeBuddyCLITransformer;