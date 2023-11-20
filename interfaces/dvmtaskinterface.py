class DVMTaskInterface:
    KIND: int
    TASK: str
    COST: int

    def NIP89_announcement(self, d_tag, content):
        """Define the NIP89 Announcement"""
        pass

    def is_input_supported(self, input_type, input_content) -> bool:
        """Check if input is supported for current Task."""
        pass

    def create_request_form_from_nostr_event(self, event, client=None, dvm_config=None) -> dict:
        """Parse input into a request form that will be given to the process method"""
        pass

    def process(self, request_form):
        "Process the data and return the result"
        pass

    @staticmethod
    def setOptions(request_form):
        print("Setting options...")
        opts = []
        if request_form.get("optStr"):
            for k, v in [option.split("=") for option in request_form["optStr"].split(";")]:
                t = (k, v)
                opts.append(t)
                print(k + "=" + v)
        print("...done.")
        return dict(opts)
