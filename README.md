# HODL token claim bot

This bot will claim your BNB rewards from the HODL token every day automatically.

[Token website](https://hodltoken.net/)

```bash
git clone https://github.com/beeb/hodlclaim.git
cd hodlclaim
poetry install --no-dev
cp hodl.service ~/.config/systemd/user/
# edit the new file in .config/systemd/user with your wallet private key
systemctl --user start hodl.service
systemctl --user enable hodl.service # run at launch
```
