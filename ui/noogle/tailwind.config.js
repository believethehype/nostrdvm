/** @type {import('tailwindcss').Config} */
export default {
    darkMode: "class",
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",

    ],
    theme: {

        extend: {
            colors: {
                'nostr': '#6d52f1',
                'nostr2': '#8453f1',

            }

        },
    },
    plugins: [require("daisyui")],
}

