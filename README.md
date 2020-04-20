# Rasa Integration Testing

This framework performs integration testing on Rasa applications by sending user inputs to a Rasa core instance channel and comparing the resulting response with the expected result.

## Scenarios

Each scenario is composed of a list of interactions which are composed of a reference to a user input and a reference to the expected bot response in a YAML format. They must be defined in a `scenarios` subfolder and can be organized in subfolders.

Each user/bot interaction content is located in a separate file. This allows reusing the same content multiple times, thus reducing the maintenance of scenarios. It also makes the scenario definition easy to write and read. Here is an example:

```yaml
- user: initial_parameters/john_johnson
  bot: welcome
- user: pay_bill/initial_intent/300$_videotron
  bot: pay_bill/account_type/collection
- user: pay_bill/account/checking
  bot: pay_bill/payment_type/collection
```

In this case, the conversion would begin with a request with the content of the `interactions/user/initial_parameters/john_johnson.json.j2` file and the response would be compared to the content of the `interactions/bot/welcome.json.j2` file. The same process will be repeated for each interaction until they are all processed or an error occurs.

### Templates

Each interaction turn is defined as a [Jinja](https://jinja.palletsprojects.com) template and can fully leverage the templating language to avoid repetition and introduce variables. Variables can be declared when refering to an interaction turn template in the scenario files. For example:

```yaml
- user:
    template: initial_parameters
    variables:
      user: john_johnson
      language: en-US
  bot:
    template: welcome
    variables:
      name: John Johnson
```

### Scenario Fragments

It is possible to create reusable scenario fragments that can be included in other scenarios. They must be defined in a `scenario_fragments` subfolder and can be organized in subfolders.

They have the same format as regular scenarios except they cannot contain references to other scenario fragments.

Here is an example of how a scenario fragment can be defined and referred:

**scenario_fragments/initial.yml**

```yaml
- user: initial_parameters/john_johnson
  bot: welcome
```

**scenarios/pay_bill.yml**

```yaml
- initial
- user: pay_bill/initial_intent/300$_videotron
  bot: pay_bill/account_type/collection
- user: pay_bill/account/checking
  bot: pay_bill/payment_type/collection
```

## Configuration

The integration tests are configured using an `INI` file. Here is an example:

```
[runner]
test_definitions_path = app/integration_tests/
ignored_result_keys = noinputTimeout,speech.confidenceLevel,speech.maxSpeechTimeout

[protocol]
type = rest
url = http://localhost:5005/webhooks/ivr/interaction
```

### `runner` section

The `runner` section has the following properties:

- `test_definitions_path`: The base directory where the scenarios and interaction definitions are located.
- `ignored_result_keys`: A comma separated list of JSON paths representing keys to be ignored when comparing the expected and actual outputs.

### `protocol` section

The `protocol` section has the following properties:

- `type`: The communication protocol type:
  - `rest` The usual value for actual integration tests. Will perform http request on an endpoint.
  - `test` An echo mode used for unit tests. The input of each interaction is returned as the output.
- `url`: The url of the Rasa connector.

## Executing tests

Integration tests can be executed using the following command:

`python -m integration_testing ...`

The available options can be found using the `--help` option.
