const Regex_Url_Str = "(https:\\/\\/)"+ "((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,})+[\\/]{0,1}" // domain name


;

const Regex_Nip05_Str= "(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\\])"

const StringUtil = {
  isValidUrl: (str: string): boolean => new RegExp(Regex_Url_Str, "i").test(str),
  parseHyperlinks: (str: string): string => str.replace(new RegExp(Regex_Url_Str, "gim"), "<a class='purple' target=\"_blank\" rel=\"noreferrer\" href=\"$&\">$&</a>").replace(new RegExp(Regex_Nip05_Str, "gim"), "<a class='purple' target=\"_blank\" rel=\"noreferrer\" href=\"https://njump.me/$&\">$&</a>"),
};

export default StringUtil;