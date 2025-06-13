import os
import json
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Directory for storing JSON data files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

EMPLOYEES_FILE = os.path.join(DATA_DIR, 'employees.json')
VACATIONS_FILE = os.path.join(DATA_DIR, 'vacations.json')
TEMPLATES_FILE = os.path.join(DATA_DIR, 'shift_templates.json')
SHIFTS_FILE = os.path.join(DATA_DIR, 'shifts.json')


def ensure_file(path, default):
    """Create file with default content if it does not exist."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.isfile(path):
        with open(path, 'w') as f:
            json.dump(default, f, indent=2)


def load_data(path, default):
    ensure_file(path, default)
    with open(path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default


def save_data(path, data):
    ensure_file(path, data)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


# Default shift templates
DEFAULT_TEMPLATES = [
    {
        "template_name": "3-smena",
        "days": ["I", "II", "III", "slobodan"],
    },
    {
        "template_name": "4-smena",
        "days": ["I", "II", "III", "IV", "slobodan"],
    },
]


@app.route('/employees', methods=['GET'])
def get_employees():
    employees = load_data(EMPLOYEES_FILE, [])
    return jsonify(employees)


@app.route('/employees/add', methods=['POST'])
def add_employee():
    data = request.get_json(force=True)
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    position = data.get('position')
    if not all([first_name, last_name, position]):
        return jsonify({'error': 'Missing employee data'}), 400

    employee = {
        'id': str(uuid.uuid4()),
        'first_name': first_name,
        'last_name': last_name,
        'position': position,
    }

    employees = load_data(EMPLOYEES_FILE, [])
    employees.append(employee)
    save_data(EMPLOYEES_FILE, employees)
    return jsonify(employee), 201


@app.route('/vacations', methods=['GET'])
def get_vacations():
    vacations = load_data(VACATIONS_FILE, [])
    return jsonify(vacations)


@app.route('/vacations/add', methods=['POST'])
def add_vacation():
    data = request.get_json(force=True)
    employee_id = data.get('employee_id')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    if not all([employee_id, start_date, end_date]):
        return jsonify({'error': 'Missing vacation data'}), 400

    try:
        sd = datetime.strptime(start_date, '%Y-%m-%d')
        ed = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    if sd > ed:
        return jsonify({'error': 'Start date must be before end date'}), 400

    vacation = {
        'id': str(uuid.uuid4()),
        'employee_id': employee_id,
        'start_date': start_date,
        'end_date': end_date,
    }
    vacations = load_data(VACATIONS_FILE, [])
    vacations.append(vacation)
    save_data(VACATIONS_FILE, vacations)
    return jsonify(vacation), 201


@app.route('/vacations/update', methods=['POST'])
def update_vacation():
    data = request.get_json(force=True)
    vac_id = data.get('id')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    if not all([vac_id, start_date, end_date]):
        return jsonify({'error': 'Missing data'}), 400

    vacations = load_data(VACATIONS_FILE, [])
    for vac in vacations:
        if vac.get('id') == vac_id:
            vac['start_date'] = start_date
            vac['end_date'] = end_date
            save_data(VACATIONS_FILE, vacations)
            return jsonify(vac)

    return jsonify({'error': 'Vacation not found'}), 404


def _get_employee_by_id(emp_id, employees):
    for emp in employees:
        if emp['id'] == emp_id:
            return emp
    return None


@app.route('/vacations/check', methods=['POST'])
def check_vacations():
    data = request.get_json(force=True)
    employee_id = data.get('employee_id')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    if not all([employee_id, start_date, end_date]):
        return jsonify({'error': 'Missing data'}), 400

    try:
        sd = datetime.strptime(start_date, '%Y-%m-%d')
        ed = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    employees = load_data(EMPLOYEES_FILE, [])
    vacations = load_data(VACATIONS_FILE, [])

    employee = _get_employee_by_id(employee_id, employees)
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    position = employee['position']
    conflicts = []
    for vac in vacations:
        if vac['employee_id'] == employee_id:
            continue
        other_emp = _get_employee_by_id(vac['employee_id'], employees)
        if not other_emp or other_emp['position'] != position:
            continue
        v_start = datetime.strptime(vac['start_date'], '%Y-%m-%d')
        v_end = datetime.strptime(vac['end_date'], '%Y-%m-%d')
        if not (ed < v_start or sd > v_end):
            conflicts.append(vac)

    return jsonify({'conflicts': conflicts})


@app.route('/shifts/generate', methods=['POST'])
def generate_shifts():
    data = request.get_json(force=True)
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    template_name = data.get('template_name')

    if not all([start_date, end_date, template_name]):
        return jsonify({'error': 'Missing data'}), 400

    try:
        sd = datetime.strptime(start_date, '%Y-%m-%d')
        ed = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    if sd > ed:
        return jsonify({'error': 'Start date must be before end date'}), 400

    templates = load_data(TEMPLATES_FILE, DEFAULT_TEMPLATES)
    template = next((t for t in templates if t['template_name'] == template_name), None)
    if not template:
        return jsonify({'error': 'Template not found'}), 404

    employees = load_data(EMPLOYEES_FILE, [])
    vacations = load_data(VACATIONS_FILE, [])

    shifts = []
    for emp in employees:
        pattern_index = 0
        current = sd
        while current <= ed:
            on_vac = False
            for vac in vacations:
                if vac['employee_id'] == emp['id']:
                    v_start = datetime.strptime(vac['start_date'], '%Y-%m-%d')
                    v_end = datetime.strptime(vac['end_date'], '%Y-%m-%d')
                    if v_start <= current <= v_end:
                        on_vac = True
                        break
            if not on_vac:
                shift_name = template['days'][pattern_index % len(template['days'])]
                shifts.append({
                    'date': current.strftime('%Y-%m-%d'),
                    'shift': shift_name,
                    'employee_id': emp['id'],
                })
                pattern_index += 1
            current += timedelta(days=1)

    save_data(SHIFTS_FILE, shifts)
    return jsonify({'message': 'Shift schedule generated', 'shifts_created': len(shifts)})


@app.route('/shifts', methods=['GET'])
def get_shifts():
    shifts = load_data(SHIFTS_FILE, [])
    return jsonify(shifts)


@app.route('/')
def index_page():
    return render_template('index.html', title='Employees')


@app.route('/vacations_page')
def vacations_page():
    return render_template('vacations.html', title='Vacations')


@app.route('/shifts_page')
def shifts_page():
    return render_template('shifts.html', title='Shifts')


@app.route('/calendar_page')
def calendar_page():
    return render_template('calendar.html', title='Calendar')


if __name__ == '__main__':
    app.run(debug=True)
