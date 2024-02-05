import { NIP05_REGEX, queryProfile } from "nostr-tools/nip05";
import { NPUB_REGEX, Nip46, PUBKEY_REGEX } from "./nip46";
import type { Nip46Response, BunkerProfile, KeyPair } from "./nip46";
import { decode, npubEncode } from "nostr-tools/nip19";
import type { UnsignedEvent } from "nostr-tools";
import { hexToBytes } from "@noble/hashes/utils";
import { checkNip05Availability } from "./utils";

type NostrIgnitionOptions = {
    appName: string;
    redirectUri: string;
    relays?: string[];
};

let options: NostrIgnitionOptions;
let nip46: Nip46;
let availableBunkers: BunkerProfile[] = [];
let localBunker: BunkerProfile | undefined = undefined;
let hasConnected = false;

const init = async (ignitionOptions: NostrIgnitionOptions) => {
    // Only do something if the window.nostr object doesn't exist
    // e.g. we don't have a NIP-07 extension
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (!(window as any).nostr) {
        console.log("Initializing Nostr Ignition...");

        const pubkey = localStorage.getItem("localNostrPubkey");
        const privkey = localStorage.getItem("localNostrPrivkey");
        if (pubkey && privkey) {
            console.log("Using local keypair");
            const keys: KeyPair = { privateKey: hexToBytes(privkey), publicKey: pubkey };
            nip46 = new Nip46(keys); // instantiate the NIP-46 class with local keys
        } else {
            console.log("Generating new keypair");
            nip46 = new Nip46(); // instantiate the NIP-46 class with no keys
        }

        options = ignitionOptions; // Set the options

        // Check for available bunkers have to do this before modal is created
        availableBunkers = await nip46.fetchBunkers();
        localBunker = availableBunkers.find((bunker) => bunker.local) || undefined;

        // Build the modal
        const modal = await createModal(); // Create the modal element

        // Get the modal elements
        const nostrModalClose = document.getElementById("nostr_ignition__nostrModalClose") as HTMLButtonElement;
        const nostrModalCreateContainer = document.getElementById("nostr_ignition__createAccount") as HTMLDivElement;
        const nostrModalConnectContainer = document.getElementById("nostr_ignition__connectAccount") as HTMLDivElement;
        const nostrModalSwitchToSignIn = document.getElementById("nostr_ignition__switchToSignIn") as HTMLButtonElement;
        const nostrModalSwitchToCreateAccount = document.getElementById(
            "nostr_ignition__switchToCreateAccount"
        ) as HTMLButtonElement;

        // Create account form
        const nostrModalNip05 = document.getElementById("nostr_ignition__nostrModalNip05") as HTMLInputElement;
        const nostrModalBunker = document.getElementById("nostr_ignition__nostrModalBunker") as HTMLSelectElement;
        const nostrModalEmail = document.getElementById("nostr_ignition__nostrModalEmail") as HTMLInputElement;
        const nostrModalCreateSubmit = document.getElementById(
            "nostr_ignition__nostrModalCreateSubmit"
        ) as HTMLButtonElement;
        const nostrModalCreateSubmitText = document.getElementById(
            "nostr_ignition__nostrModalCreateSubmitText"
        ) as HTMLSpanElement;
        const nostrModalCreateSubmitSpinner = document.getElementById(
            "nostr_ignition__nostrModalCreateSubmitSpinner"
        ) as HTMLSpanElement;
        const nostrModalNip05Error = document.getElementById("nostr_ignition__nostrModalNip05Error") as HTMLSpanElement;
        const nostrModalBunkerError = document.getElementById(
            "nostr_ignition__nostrModalBunkerError"
        ) as HTMLSpanElement;

        // Sign in form
        const nostrModalNpubOrNip05 = document.getElementById(
            "nostr_ignition__nostrModalNpubOrNip05"
        ) as HTMLInputElement;
        const nostrModalNpubOrNip05Error = document.getElementById(
            "nostr_ignition__nostrModalNpubOrNip05Error"
        ) as HTMLSpanElement;
        const nostrModalSignInSubmit = document.getElementById(
            "nostr_ignition__nostrModalSignInSubmit"
        ) as HTMLButtonElement;
        const nostrModalSignInSubmitText = document.getElementById(
            "nostr_ignition__nostrModalSignInSubmitText"
        ) as HTMLSpanElement;
        const nostrModalSignInSubmitSpinner = document.getElementById(
            "nostr_ignition__nostrModalSignInSubmitSpinner"
        ) as HTMLSpanElement;

        const SIGNIN_TIMEOUT = 10000; // 10 seconds
        let signInTimeoutFunction: NodeJS.Timeout | null = null;

        // If we had local keys, default to the sign in form
        if (pubkey && privkey) {
            nostrModalCreateContainer.style.display = "none";
            nostrModalConnectContainer.style.display = "block";
        }

        // Update the app name safely (escaping content provided by user)
        const appName = document.getElementById("nostr_ignition__appName") as HTMLSpanElement;
        appName.innerText = options.appName;

        // Add the available bunkers to the select element safely
        // (escaping content provided by user generated events)
        availableBunkers.forEach((bunker) => {
            const option = document.createElement("option");
            option.setAttribute("value", bunker.domain);
            option.innerText = bunker.domain;
            nostrModalBunker.appendChild(option);
        });

        // Create the window.nostr object and anytime it's called, show the modal
        Object.defineProperty(window, "nostr", {
            get: function () {
                showModal(modal);
            },
        });

        // Function to reset forms
        const resetForms = () => {
            if (signInTimeoutFunction) clearTimeout(signInTimeoutFunction);
            nostrModalNip05.value = "";
            nostrModalNip05.classList.remove("invalid");
            nostrModalBunkerError.classList.remove("invalid");
            nostrModalNip05Error.style.display = "none";
            nostrModalBunkerError.style.display = "none";
            nostrModalCreateSubmit.disabled = false;
            nostrModalCreateSubmitText.style.display = "block";
            nostrModalCreateSubmitSpinner.style.display = "none";
            nostrModalNpubOrNip05.value = "";
            nostrModalNpubOrNip05.classList.remove("invalid");
            nostrModalNpubOrNip05Error.style.display = "none";
            nostrModalSignInSubmit.disabled = false;
            nostrModalSignInSubmitText.style.display = "block";
            nostrModalSignInSubmitSpinner.style.display = "none";
            nostrModalCreateContainer.style.display = "none";
            nostrModalConnectContainer.style.display = "block";
            modal.close();
        };

        // Add event listener to close the modal
        nostrModalClose.addEventListener("click", function () {
            modal.close();
        });

        // Add event listeners to switch between sign in and create account
        nostrModalSwitchToSignIn.addEventListener("click", function () {
            nostrModalCreateContainer.style.display = "none";
            nostrModalConnectContainer.style.display = "block";
        });

        nostrModalSwitchToCreateAccount.addEventListener("click", function () {
            nostrModalCreateContainer.style.display = "block";
            nostrModalConnectContainer.style.display = "none";
        });

        /**
         *
         * Create account form
         *
         */

        // Add event listener to the username input to check availability
        nostrModalNip05.addEventListener("input", function () {
            checkNip05Availability(`${nostrModalNip05.value}@${nostrModalBunker.value}`, localBunker).then(
                (available) => {
                    if (available) {
                        nostrModalNip05.setCustomValidity("");
                        nostrModalCreateSubmit.disabled = false;
                        nostrModalNip05.classList.remove("invalid");
                        nostrModalNip05Error.style.display = "none";
                        nostrModalBunkerError.style.display = "none";
                    } else {
                        nostrModalCreateSubmit.disabled = true;
                        nostrModalNip05.setCustomValidity("Username is not available");
                        nostrModalNip05.classList.add("invalid");
                        nostrModalNip05Error.style.display = "block";
                    }
                }
            );
        });

        // Add an event listener to the form to create the account
        nostrModalCreateSubmit.addEventListener("click", async function (event) {
            event.preventDefault();

            nostrModalCreateSubmit.disabled = true;
            nostrModalCreateSubmitText.style.display = "none";
            nostrModalCreateSubmitSpinner.style.display = "block";

            const bunkerPubkey = availableBunkers.find((bunker) => bunker.domain === nostrModalBunker.value)?.pubkey;

            // Add error if we don't have valid details
            if (!nostrModalBunker.value || !bunkerPubkey) {
                nostrModalCreateSubmit.disabled = true;
                nostrModalBunker.setCustomValidity("Error creating account. Please try again later.");
                nostrModalBunker.classList.add("invalid");
                nostrModalBunkerError.style.display = "block";
                // Remove spinner and re-enable submit button
                nostrModalCreateSubmit.disabled = false;
                nostrModalCreateSubmitText.style.display = "block";
                nostrModalCreateSubmitSpinner.style.display = "none";
                return;
            }

            // Trigger the create account flow
            createAccount(
                bunkerPubkey,
                nostrModalNip05.value,
                nostrModalBunker.value,
                nostrModalEmail.value || undefined
            )
                .then((response) => {
                    if (response && response.error) {
                        openNewWindow(`${response.error}?redirect_uri=${options.redirectUri}`);
                    }
                })
                .catch((error) => console.error(error));
        });

        /**
         *
         * Sign in form
         *
         */

        // Add event listener to enable submit button
        nostrModalNpubOrNip05.addEventListener("input", function () {
            nostrModalNpubOrNip05Error.innerText = "";
            nostrModalNpubOrNip05Error.style.display = "none";
            nostrModalNpubOrNip05.classList.remove("invalid");
            if (nostrModalNpubOrNip05.value.length > 0) {
                nostrModalSignInSubmit.disabled = false;
            } else {
                nostrModalSignInSubmit.disabled = true;
            }
        });

        // Add event listener for sign in form
        nostrModalSignInSubmit.addEventListener("click", async function (event) {
            event.preventDefault();
            nostrModalSignInSubmit.disabled = true;
            nostrModalSignInSubmitText.style.display = "none";
            nostrModalSignInSubmitSpinner.style.display = "block";

            let remotePubkey: string | null = null;
            // Order is important here. NIP05_REGEX is pretty loose so it will match an npub
            if (NPUB_REGEX.test(nostrModalNpubOrNip05.value)) {
                // Decode pubkey from npub
                remotePubkey = decode(nostrModalNpubOrNip05.value).data as string;
            } else if (PUBKEY_REGEX.test(nostrModalNpubOrNip05.value)) {
                // Looks like a pubkey
                remotePubkey = nostrModalNpubOrNip05.value;
            } else if (NIP05_REGEX.test(nostrModalNpubOrNip05.value)) {
                // Look up pubkey for nip05
                const profilePointer = await queryProfile(nostrModalNpubOrNip05.value);
                if (profilePointer) {
                    remotePubkey = profilePointer.pubkey;
                } else {
                    nostrModalNpubOrNip05.setCustomValidity("Error fetching Pubkey from NIP-05 value.");
                    nostrModalNpubOrNip05.classList.add("invalid");
                    nostrModalNpubOrNip05Error.innerText = "Error fetching Pubkey from NIP-05 value.";
                    nostrModalNpubOrNip05Error.style.display = "block";
                    // Remove spinner and re-enable submit button
                    nostrModalSignInSubmit.disabled = false;
                    nostrModalSignInSubmitText.style.display = "block";
                    nostrModalSignInSubmitSpinner.style.display = "none";
                    return;
                }
            } else {
                // Nothing matches the value - it's an error.
                nostrModalNpubOrNip05.setCustomValidity("Invalid Pubkey, npub, or NIP-05");
                nostrModalNpubOrNip05.classList.add("invalid");
                // Remove spinner and re-enable submit button
                nostrModalSignInSubmit.disabled = false;
                nostrModalSignInSubmitText.style.display = "block";
                nostrModalSignInSubmitSpinner.style.display = "none";
                return;
            }

            connect(remotePubkey)
                .then((response) => {
                    if (response && response.result === "ack") {
                        hasConnected = true;
                        resetForms();
                    }
                })
                .catch((error) => console.error(error));

            signInTimeoutFunction = setTimeout(() => {
                nostrModalNpubOrNip05Error.innerText =
                    "No response from a remote signer. Are you sure there is an available remote signer managing this Pubkey?";
                nostrModalNpubOrNip05Error.style.display = "block";
                // Remove spinner and re-enable submit button
                nostrModalSignInSubmit.disabled = false;
                nostrModalSignInSubmitText.style.display = "block";
                nostrModalSignInSubmitSpinner.style.display = "none";
            }, SIGNIN_TIMEOUT);
        });

        nip46.on("authChallengeSuccess", async (response: Nip46Response) => {
            if (response.result === "ack") {
                console.log("Connected to bunker");
                hasConnected = true;
                resetForms();
            } else if (response.result === "pong") {
                console.log("Pong!");
            } else if (PUBKEY_REGEX.test(response.result)) {
                console.log("Account created with pubkey: ", response.result);
                nip46.remotePubkey = response.result;
                hasConnected = true;
                resetForms();
            }
        });
    }
};

// Function to create and show the modal using <dialog>
const createModal = async (): Promise<HTMLDialogElement> => {
    // Create the dialog element
    const dialog: HTMLDialogElement = document.createElement("dialog");
    dialog.id = "nostr_ignition__nostrModal";

    // Add content to the dialog
    const dialogContent: HTMLDivElement = document.createElement("div");
    dialogContent.innerHTML = `
        <button id="nostr_ignition__nostrModalClose"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-x-square"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg></button>
        <h2 id="nostr_ignition__nostrModalTitle"><span id="nostr_ignition__appName">This app</span> uses Nostr for accounts</h2>
        <div id="nostr_ignition__createAccount">
            <p>Would you like to create a new Nostr account? Identities on Nostr are portable so you'll be able to use this account on any other Nostr client.</p>
            <form id="nostr_ignition__nostrCreateAccountForm" class="nostr_ignition__nostrModalForm">
                <span class="nostr_ignition__inputWrapper">
                    <input type="text" id="nostr_ignition__nostrModalNip05" name="nostrModalNip05" placeholder="Username" required />
                    <select id="nostr_ignition__nostrModalBunker" name="nostrModalBunker" required>
                    </select>
                </span>
                <span id="nostr_ignition__nostrModalNip05Error" class="nostr_ignition__nostrModalError">Username not available</span>
                <span id="nostr_ignition__nostrModalBunkerError" class="nostr_ignition__nostrModalError">Error creating account</span>
                <span class="nostr_ignition__inputWrapperFull">
                    <input type="email" id="nostr_ignition__nostrModalEmail" name="nostrModalEmail" placeholder="Email address. Optional, for account recovery." />
                </span>
                <button type="submit" id="nostr_ignition__nostrModalCreateSubmit" disabled>
                    <span id="nostr_ignition__nostrModalCreateSubmitText">Create account</span>
                    <span id="nostr_ignition__nostrModalCreateSubmitSpinner"></span>
                </button>
            </form>
            <button id="nostr_ignition__switchToSignIn" class="nostr_ignition__linkButton">Already have a Nostr account? Sign in instead.</button>
        </div>
        <div id="nostr_ignition__connectAccount" style="display:none;">
            <p style="text-align: center;">Sign in with your Pubkey, npub, or NIP-05.</p>
            <form id="nostr_ignition__nostrSignInForm" class="nostr_ignition__nostrModalForm">
                <span class="nostr_ignition__inputWrapper">
                    <input type="text" id="nostr_ignition__nostrModalNpubOrNip05" name="nostrModalNpubOrNip05" placeholder="Pubkey, npub, or NIP-05" required />
                </span>
                <span id="nostr_ignition__nostrModalNpubOrNip05Error" class="nostr_ignition__nostrModalError"></span>
                <button type="submit" id="nostr_ignition__nostrModalSignInSubmit" disabled>
                    <span id="nostr_ignition__nostrModalSignInSubmitText">Sign in</span>
                    <span id="nostr_ignition__nostrModalSignInSubmitSpinner"></span>
                </button>
            </form>
            <button id="nostr_ignition__switchToCreateAccount" class="nostr_ignition__linkButton">No Nostr account? Create a new account.</button>
        </div>
        <div id="nostr_ignition__nostrModalLearnMore">Not sure what Nostr is? Check out <a href="https://nostr.how" target="_blank">Nostr.how</a> for more info</div>
    `;
    dialog.appendChild(dialogContent);

    // Append the dialog to the document body
    document.body.appendChild(dialog);
    return dialog;
};

// Function to show the modal
const showModal = (dialog: HTMLDialogElement): void => {
    dialog.showModal();
};

/**
 * Opens a new window with the specified URL.
 * @param url - The URL to open in the new window.
 */
const openNewWindow = (url: string): void => {
    const width = 600; // Desired width of the window
    const height = 800; // Desired height of the window

    const windowFeatures = `width=${width},height=${height},popup=yes`;
    window.open(url, "nostrIgnition", windowFeatures);
};

const remoteNpub = (): string | null => {
    return nip46.remotePubkey ? npubEncode(nip46.remotePubkey) : null;
};

const remotePubkey = (): string | null => {
    return nip46.remotePubkey;
};

const connected = (): boolean => {
    return hasConnected;
};

const connect = async (remotePubkey: string): Promise<Nip46Response | void> => {
    console.log("Connecting to bunker...");
    return nip46
        .connect(remotePubkey)
        .then((response) => {
            if (response.result === "auth_url" && response.error) {
                openNewWindow(`${response.error}?redirect_uri=${options.redirectUri}`);
            }
            return response;
        })
        .catch((error) => console.error(error));
};

const createAccount = async (
    bunkerPubkey: string,
    username: string,
    domain: string,
    email?: string
): Promise<Nip46Response | void> => {
    console.log("Creating account...");
    return nip46
        .createAccount(bunkerPubkey, username, domain, email)
        .then((response) => response)
        .catch((error) => console.error(error));
};

const ping = async (): Promise<Nip46Response | void> => {
    console.log("Pinging bunker...");
    nip46
        .ping()
        .then((response) => {
            if (response.result === "pong") {
                console.log("Pong!");
            } else if (response.result === "auth_url" && response.error) {
                openNewWindow(`${response.error}?redirect_uri=${options.redirectUri}`);
            }
            return response;
        })
        .catch((error) => console.error(error));
};

const signEvent = async (event: UnsignedEvent): Promise<Nip46Response | void> => {
    console.log("Requesting signature...");
    return nip46
        .sign_event(event)
        .then((response) => {
            if (response.result === "auth_url" && response.error) {
                openNewWindow(`${response.error}?redirect_uri=${options.redirectUri}`);
            } else {
                console.log("Signed event:", JSON.parse(response.result));
            }
            return response;
        })
        .catch((error) => {
            console.error(error);
        });
};

export default {
    init,
    createAccount,
    ping,
    connect,
    signEvent,
    remoteNpub,
    remotePubkey,
    connected,
};
