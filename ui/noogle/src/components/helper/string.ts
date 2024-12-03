const Regex_Url_Str = "^https?:\/\/(?:.*\/)?[^\/.]+$" // domain name
const Regex_Url_Img = "(https?:\\/\\/.*\\.(?:png|jpg|jpeg|webp|gif))" // domain name
const Regex_Url_Video = "(https?:\\/\\/.*\\.(?:mp4|mov|avi))" // domain name
const Regex_Urlw_Str = "(https:\\/\\/)" + "((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,})+[\\/]{0,1}" // domain name

;

const Regex_Nip05_Str = "(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\\])"

const StringUtil = {
    isValidUrl: (str: string): boolean => new RegExp(Regex_Url_Str, "i").test(str),
    parseHyperlinks: (str: string): string => str.replace(new RegExp(Regex_Urlw_Str, "gim"), "<a class='purple' target=\"_blank\" rel=\"noreferrer\" href=\"$&\">$&</a>").replace(new RegExp(Regex_Nip05_Str, "gim"), "<a class='purple' target=\"_blank\" rel=\"noreferrer\" href=\"https://njump.me/$&\">$&</a> "),
    parseImages: (str: string): string => str.toLowerCase().includes('nsfw') || str.toLowerCase().includes('lingerie') || str.toLowerCase().includes('sex') || str.toLowerCase().includes('porn') ? str.replace(" http", "\nhttp").replace(new RegExp(Regex_Url_Img, "gim"), "<details><summary class=\"collapse-title   \"><div class=\"btn\">NSFW Show/Hide Results</div></summary><img src='$&'/></div></details> ").replace(new RegExp(Regex_Url_Video, "gim"), "<details><summary class=\"collapse-title   \"><div class=\"btn\">NSFW Show/Hide Results</div><video controls muted autoplay src=\"$&\"></video></summary></details>").replace(new RegExp(Regex_Url_Str, "gim"), "<a class='purple' target=\"_blank\" rel=\"noreferrer\" href=\"$&\">$&</a> ") : str.replace(" http", "\nhttp").replace(new RegExp(Regex_Url_Img, "gim"), "<img src='$&'/> ").replace(new RegExp(Regex_Url_Video, "gim"), "<video controls muted autoplay src=\"$&\"></video> ").replace(new RegExp(Regex_Url_Str, "gim"), "<a class='purple' target=\"_blank\" rel=\"noreferrer\" href=\"$&\">$&</a> "),
    parseImages_save: (str: string): string =>   str.replace(" http", "\nhttp").replace(str, "<img src='$&'/> ").replace(new RegExp(Regex_Url_Video, "gim"), "<video controls muted autoplay src=\"$&\"></video> ").replace(new RegExp(Regex_Url_Str, "gim"), "<a class='purple' target=\"_blank\" rel=\"noreferrer\" href=\"$&\">$&</a> "),


    //parseImages: (str: string): string => str.replace(" http", "<br>http") //.replace("\n", " ").replace(new RegExp(Regex_Url_Img, "gim"), "<img src='$&'/> ")


};

export default StringUtil;