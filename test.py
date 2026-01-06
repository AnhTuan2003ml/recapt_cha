from freecaptcha import reCAPTCHAV3Solver

token = reCAPTCHAV3Solver.solve("https://www.google.com/recaptcha/enterprise/anchor?ar=1&k=6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV&co=aHR0cHM6Ly9sYWJzLmdvb2dsZTo0NDM.&hl=en&v=7gg7H51Q-naNfhmCP3_R47ho&size=invisible&anchor-ms=20000&execute-ms=30000&cb=jx6vinm8gina")

# Use token within your HTTP request
print(token)