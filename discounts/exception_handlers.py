from rest_framework.views import exception_handler


def _single_field_message(errors: dict) -> str | None:
    if len(errors) != 1:
        return None
    field, messages = next(iter(errors.items()))
    if isinstance(messages, list) and messages:
        return str(messages[0])
    return None


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    data = response.data
    if isinstance(data, dict):
        if "detail" in data and len(data) == 1:
            detail = data["detail"]
            if isinstance(detail, list):
                message = str(detail[0])
            else:
                message = str(detail)
            response.data = {"message": message, "errors": {}}
        else:
            non_field = data.get("non_field_errors")
            if non_field:
                message = str(non_field[0])
                errors = {
                    key: value for key, value in data.items() if key != "non_field_errors"
                }
            else:
                single_message = _single_field_message(data)
                if single_message:
                    message = single_message
                    errors = data
                else:
                    message = "Validation failed."
                    errors = data
            response.data = {"message": message, "errors": errors}
    elif isinstance(data, list):
        response.data = {"message": str(data[0]), "errors": {}}

    return response
