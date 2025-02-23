#!/usr/bin/python
# -*- coding: utf-8 -*-
# -----------------------------------------
# Phantom sample App Connector python file
# -----------------------------------------

# Phantom App imports
import phantom.app as phantom
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
# from test_monday_andre_consts import *
import requests
import json
from bs4 import BeautifulSoup
from monday import MondayClient

class RetVal(tuple):

    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class Test_Monday_AndreConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(Test_Monday_AndreConnector, self).__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR, "Empty response and no information in the header"
            ), None
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code, error_text)

        message = message.replace(u'{', '{{').replace(u'}', '}}')
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}".format(str(e))
                ), None
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
            r.status_code,
            r.text.replace(u'{', '{{').replace(u'}', '}}')
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, 'add_debug_data'):
            action_result.add_debug_data({'r_status_code': r.status_code})
            action_result.add_debug_data({'r_text': r.text})
            action_result.add_debug_data({'r_headers': r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if 'json' in r.headers.get('Content-Type', ''):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if 'html' in r.headers.get('Content-Type', ''):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            r.status_code,
            r.text.replace('{', '{{').replace('}', '}}')
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="post", **kwargs):
        config = self.get_config()
        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
            action_result.set_status(phantom.APP_ERROR, "Invalid method: {0}".format(method)),
            resp_json
            )

    # Create a URL to connect to
        url = self._base_url + endpoint

        headers = kwargs.pop('headers', {})
        headers.update({
            'Authorization': self._api_token,
            'Content-Type': 'application/json'
        })

        try:
            r = request_func(
                url,
                headers=headers,
                verify=config.get('verify_server_cert', False),
                **kwargs
            )
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, "Error Connecting to server. Details: {0}".format(str(e))
                ), resp_json
            )

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.

        self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, response = self._make_rest_call(
            '/endpoint', action_result, params=None, headers=None
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Test Connectivity Failed.")
            # return action_result.get_status()

        # Return success
        # self.save_progress("Test Connectivity Passed")
        # return action_result.set_status(phantom.APP_SUCCESS)

        # For now return Error with a message, in case of success we don't set the message, but use the summary
        return action_result.set_status(phantom.APP_ERROR, "Action not yet implemented")

    def _handle_create_item(self, param):
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        action_result = self.add_action_result(ActionResult(dict(param)))

        board_id = param.get('board_id')
        group_id = param.get('group_id')
        item_name = param.get('item_name')
        if not board_id or not group_id or not item_name:
            return action_result.set_status(phantom.APP_ERROR, "Missing required parameters")
    
        monday=MondayClient(self._api_token)

        item = monday.items.create_item(board_id=param.get('board_id', ''), group_id=param.get('group_id', ''), item_name=param.get('item_name', ''))
        
        # Extract the item_id from the response
        item_id = item.get('id', 'N/A')
        
        # Add the board_id and item_id to the data section
        result_data = {
            'item_id': item_id,
            'board_id': board_id
        }
        action_result.add_data(result_data)
    
        # Add the item_id to the summary
        summary = action_result.update_summary({})
        summary['board_id'] = board_id
        # Add the response data to the action result

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_fetch_boards(self, param):
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        action_result = self.add_action_result(ActionResult(dict(param)))

        board_id = param.get('board_id')
        my_board_ids = [board_id]

        if not board_id:
            return action_result.set_status(phantom.APP_ERROR, "Missing required parameters")

        monday = MondayClient(self._api_token)

        try:
            # Fetch board details
            item = monday.boards.fetch_boards_by_id(board_ids=my_board_ids)
            self.debug_print("Board Details:", item)

            # Check if the response contains board details
            if not item or 'data' not in item or 'boards' not in item['data'] or not item['data']['boards']:
                return action_result.set_status(phantom.APP_ERROR, "No board details found")

            # Assuming single board ID, so fetch the first board's details
            board = item['data']['boards'][0]

            # Prepare result data
            result_data = {
                'board_id': board.get('id', 'N/A'),
                'board_name': board.get('name', 'N/A'),
                'permissions': board.get('permissions', 'N/A'),
                'tags': board.get('tags', []),
                'groups': [],
                'group_ids': [],
                'columns': []
            }

            # Extract groups information
            for group in board.get('groups', []):
                result_data['groups'].append({
                    'group_id': group.get('id', 'N/A'),
                    'group_title': group.get('title', 'N/A')
                })
                result_data['group_ids'].append(group.get('id', 'N/A'))

            # Extract columns information
            for column in board.get('columns', []):
                result_data['columns'].append({
                    'column_id': column.get('id', 'N/A'),
                    'column_title': column.get('title', 'N/A'),
                    'column_type': column.get('type', 'N/A'),
                    'column_settings': column.get('settings_str', 'N/A')
                })

            # Add the fetched board details to the action result
            action_result.add_data(result_data)

            # Update the summary
            summary = action_result.update_summary({})
            summary['board_id'] = board_id
            summary['board_name'] = board.get('name', 'N/A')  # Add board name to summary for better visibility

            return action_result.set_status(phantom.APP_SUCCESS)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Failed to fetch board details. Error: {0}".format(str(e)))
        
    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'create_item':
            ret_val = self._handle_create_item(param)

        if action_id == 'fetch_boards':
            ret_val = self._handle_fetch_boards(param)

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        # Commented out by Andre self._base_url = config.get('base_url')
        self._base_url = "https://api.monday.com"
        self._api_token = config.get('api_token')

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:

        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = Test_Monday_AndreConnector._get_phantom_base_url() + '/login'

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = Test_Monday_AndreConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == '__main__':
    main()