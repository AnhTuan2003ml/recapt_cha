from endpoints import ant_endpoint, twocap_endpoint, google_flow_endpoint
from src import CaptchaSolver, HttpClient, RichConsole

# * PROXY URL examples
# "http://username:password@host:port"
# "socks5://username:password@host:port"

VERBOSE = True
LOG_HANDLER = True
PROXY_URL = None

ANT_URL = "https://antcpt.com/score_detector/"
TWO_URL = "https://2captcha.com/demo/recaptcha-v3-enterprise"
GOOGLE_FLOW_URL = "https://labs.google"
GOOGLE_FLOW_SITEKEY = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"
GOOGLE_FLOW_ANCHOR_URL = "https://www.google.com/recaptcha/enterprise/anchor?ar=1&k=6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV&co=aHR0cHM6Ly9sYWJzLmdvb2dsZTo0NDM.&hl=en&v=7gg7H51Q-naNfhmCP3_R47ho&size=invisible&anchor-ms=20000&execute-ms=30000&cb=yv0004astgfg"


def get_ip(client):
    """
    Retrieves the public IP address using the provided HTTP client.

    Args:
        client: The HTTP client used to make the request.

    Returns:
        str: The public IP address extracted from the JSON response.
    """
    response = client.get("https://jsonip.com/")
    return response.json()["ip"]


# TODO: Implement this section below based on the website that needs to be bypassed.
def solve_v3(is_ant=False, is_two=False, is_google_flow=False):
    BASE_URL = ANT_URL if is_ant else TWO_URL if is_two else GOOGLE_FLOW_URL if is_google_flow else None

    if BASE_URL is None:
        raise ValueError("Either 'is_ant', 'is_two', or 'is_google_flow' must be True")

    custom_sitekey = GOOGLE_FLOW_SITEKEY if is_google_flow else None
    custom_anchor_url = GOOGLE_FLOW_ANCHOR_URL if is_google_flow else None
    solver = CaptchaSolver(BASE_URL, VERBOSE, custom_sitekey, custom_anchor_url)

    with HttpClient(PROXY_URL, LOG_HANDLER) as client:
        ip_address = get_ip(client)
        user_agent = client.base_agent["User-Agent"]
        captcha_token = solver.solve_captcha(client)
        page_action = "FLOW_GENERATION" if is_google_flow else solver.page_action

        if is_two:
            sitekey = solver.sitekey
            return twocap_endpoint(
                client, sitekey, captcha_token, page_action, user_agent, ip_address
            )
        elif is_ant:
            return ant_endpoint(
                client, captcha_token, page_action, user_agent, ip_address
            )
        elif is_google_flow:
            return google_flow_endpoint(
                client, solver.sitekey, captcha_token, page_action, user_agent, ip_address
            )


if __name__ == "__main__":
    RichConsole.clear()
    RichConsole.print(solve_v3(is_google_flow=True))
