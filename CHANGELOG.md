# Changelog

All notable changes to hafermilch are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Commits follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) spec.

## [0.1.2] — 2026-03-10

### CI

- Adapt the tests for latest changes ([`b69f007`](b69f00744fbd9a319305e041cec588a9ce130f64))

### Features

- Document the agent interactions on html ([`bca7c2e`](bca7c2e0b10180e8d6fb2bacfa42d2d9752f27d7))
- Show token usage stats ([`7301528`](7301528f6a2d6c61624baf1a6ffeed88ab741196))
- Optimize LLM calls for minimal actions. Ex: 1 action for a Login step ([`7c7f5d9`](7c7f5d9c9734c06a44a1e8dbd1a15554b0f906c2))

### Miscellaneous

- Provide good info on hte logs ([`b599b24`](b599b2481c64c571156e1bb1d6ed08232341a237))
- Build includes jinja for beautiful HTML reports ([`da9427b`](da9427b6b6eb703b961710feeef076fd14926beb))
- Update CHANGELOG for v0.1.1 ([`001a9da`](001a9daaab3d093ad873fcc638871fee685d3e6a))

## [0.1.1] — 2026-03-09

### Documentation

- Show github stats ([`c28101b`](c28101b07995b0398e235e0691ba821db72df555))

### Features

- Set credentials as env variables for task that involves logging in ([`ba4199e`](ba4199ec55869ca80428492f4d177e19a9ca54fa))
- Provide some reasonable outputs during headless mode ([`d8a7fac`](d8a7fac99bbb8b37aa1e9a314d000d1a022d16db))
- Use litellm for centralized model gateway ([`e842163`](e842163f558646e70763edd039ebe891f94ad515))

### Miscellaneous

- Update examples on how to use login ([`c3ffe49`](c3ffe4904fd9c691885703365763ae544fb94415))
- Ignore some local files ([`7e29a91`](7e29a914a80961de450de7aaa76350f6d31f2ccc))
- Update CHANGELOG for v0.1.0 ([`e1580b0`](e1580b0d49d3977656bfb1830ea900d08d48895a))

### Refactoring

- Fix some trivial issues ([`59b4517`](59b4517967bba9b7aa0018bb8ee5514e266a6b2e))

### Build

- Migrate to litellm ([`f4c5e52`](f4c5e5231920b8e2a104f7bf2a882245d000480d))

## [0.1.0] — 2026-03-08

### CI

- Give some docs love ([`fad492f`](fad492f0f5b4175937d25221e2d0228ae5f866a7))
- Install github actions ([`633992a`](633992ad283642c864235d57b65ef32f80c848fc))
- Make nox x ruff happy ([`9b4f3ee`](9b4f3ee75534ccbdfd52167f17af6a2080293f05))
- Provide some tests to make hafermilch stealthy ([`3a63b3d`](3a63b3d12293416ab2566f35c611e54ac8efa6b8))
- Update depedencies ([`4d22109`](4d22109861b7633292098f695922b3b81cc3d350))
- Make ruff happy ([`c5b099f`](c5b099f8e191316a4690858bdd3003d6afc3d679))

### Documentation

- More love to it ([`42d8200`](42d8200faf456f41fa5408f7029b3063e164e682))
- Install agent browser from correct place ([`6be3cee`](6be3cee4000b165d4790fb75ac571fd40ee5128b))
- Explain usage of different browser backends ([`fada1ab`](fada1ab57cb185f3343e3c7f7a9846c4af8f25be))
- How to use Hafermilch ([`8aa6b85`](8aa6b85ce9b1e49ba3352702312c5aba8e8012c9))

### Features

- Introduce arugment to choose browser backends ([`f62ee6e`](f62ee6e89fb552e59345ad12019ecad12d2c9076))
- Adapt evaluation for two possible browser backends ([`c478180`](c4781806e8201056c0fc1af8d5b0e267c2fe796a))
- Provide usage of agent-browser from vercel ([`d9c561a`](d9c561a4c470ab874ebf7e2fc6abb590071860a5))
- Initial commits of hafermilch ([`edc2e5a`](edc2e5aac2ef3ec97f3ca0d22b1f2edb5baeaac4))

### Miscellaneous

- Few fixes and doc updates ([`6c82863`](6c828637c6dc0f834755826c69c2afdc83f28f02))
- Provide some example config files ([`e1284d2`](e1284d2549963d847432f18a592d6b4aa23e912d))
- Provide sample .env ([`4b78d3b`](4b78d3ba1a66d50d34f9630f594487236c0ad8be))

### Build

- Relase the package to pypi ([`4b656b7`](4b656b7384d19561d7e76147010486bb1e5a11ed))
- Track dependencies ([`65f8b2e`](65f8b2ecc5af6557cdf795a7536e2205ac1b3609))
- Initial repo setup ([`b4d5c64`](b4d5c6431e86c542d6e96c5ceafb80b732d9d32d))


