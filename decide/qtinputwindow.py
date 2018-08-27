import os
import sys
import uuid
from collections import defaultdict

from PyQt5 import QtWidgets, QtCore

from decide.cli import init_model
from decide.model.base import ActorIssue
from decide.model.helpers import csvparser
from decide.model.helpers.helpers import data_file_path


def open_file(path):
    import subprocess, os
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', path))
    elif os.name == 'nt':
        os.startfile(path)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', path))


def clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                clear_layout(item.layout())


class DoubleInput(QtWidgets.QLineEdit):

    def __init__(self):
        super(DoubleInput, self).__init__()

        self.setFixedWidth(75)

    def setValue(self, value):

        self.setText(str(value))

    @property
    def valueChanged(self):
        return self.textChanged


class Observer:
    """
    Listener
    """
    key = 'AbstractObserver'

    def add(self, observer, value):
        raise NotImplementedError

    def delete(self, observer, row):
        raise NotImplementedError

    def change(self, observer, key, value):
        raise NotImplementedError


class Observable:
    """
    Event
    """

    def __init__(self):
        self.observers = []

    def notify_add(self, value):
        for observer in self.observers:
            observer.add(self, value)

    def notify_delete(self, row):

        for observer in self.observers:
            observer.delete(self, row)

    def notify_change(self, key, value):
        for observer in self.observers:
            observer.change(self, key, value)

    def register(self, obj):
        self.observers.append(obj)


class PrintObserver(Observer):
    """
    For debugging
    """

    def add(self, observer, value):
        pass
        # print('add')
        # print(observer)
        # print(value)

    def delete(self, observer, row):
        pass
        # print('delete')
        # print(observer)
        # print(row)

    def change(self, observer, key, value):
        pass
        # print('change')
        # print(observer)
        # print(key)
        # print(value)


class ActorInput(Observable):
    """
    Object containing a name and power
    """

    def __init__(self, name, power):
        super().__init__()
        self.id = None
        self._name = name
        self._power = power
        self.key = 'actor_input'

        self.register(PrintObserver())

        self.uuid = uuid.uuid4()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self.set_name(value)

    @property
    def power(self):
        return self._power

    @power.setter
    def power(self, value):
        self.set_power(value)

    def set_name(self, value, silence=False):
        self._name = value

        if not silence:
            self.notify_change('name', value)

    def set_power(self, value, silence=False):

        self._power = value

        if not silence:
            self.notify_change('power', value)


class IssueInput(Observable):
    """
    Object containing a name, lower and upper bounds
    """

    def __init__(self, name, lower, upper):
        super().__init__()
        self.id = None
        self._name = name
        self._lower = lower
        self._upper = upper
        self.key = 'issue_input'

        self.register(PrintObserver())

        self.uuid = uuid.uuid4()

    @property
    def name(self):
        return self._name

    @property
    def lower(self):
        return self._lower

    @property
    def upper(self):
        return self._upper

    @name.setter
    def name(self, value):
        self.set_name(value)

    @lower.setter
    def lower(self, value):
        self.set_lower(value)

    @upper.setter
    def upper(self, value):
        self.set_upper(value)

    def set_name(self, value):
        self._name = value
        self.notify_change('name', value)

    def set_lower(self, value):
        self._lower = value
        self.notify_change('lower', value)

    def set_upper(self, value):
        self._upper = value
        self.notify_change('upper', value)


class ActorIssueInput(Observer, Observable):

    def add(self, key=None, value=None):
        self.actor_input.setText(self.actor.name)
        self.issue_input.setText(self.issue.name)
        self.power_input.setText(self.actor.power)

    def delete(self, observer, row):
        """
        Remove ... this row when the actor or issue is deleted
        """
        print('delete this actor issue')

    def change(self, observer, key, value):

        if isinstance(observer, ActorInput):
            if key == 'name':
                self.actor_input.setText(value)
                self.notify_change('choices', True)
            if key == 'power':
                self.power_input.setText(str(value))

        if isinstance(observer, IssueInput):
            if key == 'name':
                self.issue_input.setText(value)
                self.notify_change('choices', True)
            if key == 'upper':
                print(value)
            if key == 'lower':
                print(value)

        if key == 'position':
            self.set_position(value)

        if key == 'power':
            self.set_power(value)

        self.notify_change('redraw', True)

    def __init__(self, actor: ActorInput, issue: IssueInput):
        super().__init__()
        self.id = None

        self.actor = actor
        self.issue = issue

        self.actor.register(self)
        self.issue.register(self)

        self.actor_input = QtWidgets.QLabel(actor.name)
        self.issue_input = QtWidgets.QLabel(issue.name)

        self.power_input = QtWidgets.QLabel(str(actor.power))

        self.position_input = DoubleInput()
        self.position_input.valueChanged.connect(self.set_position)

        self.salience_input = DoubleInput()

        self.meta = dict()

        self.uuid = uuid.uuid4()

        self._power = 0.0
        self._position = 0.0
        self._salience = 0.0

    @property
    def position(self):
        return self._position

    @property
    def salience(self):
        return self._salience

    @property
    def power(self):
        return self._power

    def set_position(self, value, silence=False):
        self._position = value
        if not silence:
            self.notify_change('position', value)

    def set_power(self, value, silence=False):
        self._power = value
        if not silence:
            self.notify_change('power', value)

    def set_salience(self, value, silence=False):
        self._salience = value
        if not silence:
            self.notify_change('salience', value)


class PositionInput(ActorIssueInput):
    """
    For editing the position
    """

    def __init__(self, actor_issue: ActorIssueInput):
        super().__init__(actor_issue.actor, actor_issue.issue)

        actor_issue.register(self)


class SalienceInput(ActorIssueInput):
    def __init__(self, actor_issue: ActorIssueInput):
        super().__init__(actor_issue.actor, actor_issue.issue)

        actor_issue.register(self)


class BoxLayout(QtWidgets.QGroupBox):

    def __init__(self, title, btn=True):
        super(BoxLayout, self).__init__(title)

        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)

        self.scroll_area_widget = QtWidgets.QWidget()
        self.scroll_area.setWidget(self.scroll_area_widget)

        self.grid_layout = QtWidgets.QGridLayout(self.scroll_area_widget)
        self.grid_layout.setAlignment(QtCore.Qt.AlignTop)

        self.layout_container = QtWidgets.QVBoxLayout()
        self.layout_container.addWidget(self.scroll_area)

        if btn:
            self.add_button = QtWidgets.QPushButton('Add')
            # self.layout_container.addWidget(QtWidgets.QTextEdit())
            self.layout_container.addWidget(self.add_button)

        self.setLayout(self.layout_container)

        self.items = {}

        self._row_pointer = 0

    def clear(self):
        clear_layout(self.grid_layout)

        self.items = {}
        self._row_pointer = 0

    def add_heading(self):
        raise NotImplementedError

    def add_row(self, *args, pointer=None):

        if pointer:
            row = pointer
        else:
            row = self._row_pointer

        for column, arg in enumerate(args):
            if isinstance(arg, str):
                arg = QtWidgets.QLabel(arg)

            self.grid_layout.addWidget(arg, row, column)

        self._row_pointer += 1

        return row

    def delete_row(self):

        sending_button = self.sender()  # type: QtWidgets.QPushButton

        print(sending_button.objectName())

        row = int(sending_button.objectName().split('-')[-1])

        obj = self.items[row]

        del self.items[row]

        for column in range(self.grid_layout.count()):

            item = self.grid_layout.itemAtPosition(row, column)
            if item:
                item.widget().deleteLater()
            self.grid_layout.removeItem(item)

        return obj


class ActorBox(BoxLayout, Observable):
    key = 'actor_box'

    def __init__(self):
        super(ActorBox, self).__init__('Actors')

        self.add_button.clicked.connect(self.add_action)

        self.register(PrintObserver())

    def add_heading(self):
        self.add_row('Actor')

    def add_actor(self, name='', power=0.0):
        actor_input = ActorInput(name, str(power))
        actor_input.id = self._row_pointer

        name_input = QtWidgets.QLineEdit()
        name_input.setText(name)
        # call the setter on a change
        name_input.textChanged.connect(actor_input.set_name)

        power_input = DoubleInput()
        power_input.setValue(power)
        power_input.valueChanged.connect(actor_input.set_power)

        delete_button = QtWidgets.QPushButton('Delete')
        delete_button.clicked.connect(self.delete_row)
        delete_button.setObjectName('actor-' + str(self._row_pointer))

        self.items[actor_input.id] = actor_input

        self.add_row(name_input, power_input, delete_button)

        return actor_input

    def add_action(self):
        a = self.add_actor()
        self.notify_add(a)

    def delete_row(self):
        row = super().delete_row()
        self.notify_delete(row)


class IssueBox(BoxLayout, Observable):
    key = 'issue_box'

    def __init__(self):
        super(IssueBox, self).__init__('Issues')

        self.add_button.clicked.connect(self.add_action)

        self.register(PrintObserver())

    def add_heading(self):
        self.add_row('Issue', 'Lower', 'Upper')

    def add_issue(self, name='', lower=0, upper=100.0):
        issue_input = IssueInput(name, lower, upper)
        issue_input.id = self._row_pointer

        lower_input = DoubleInput()
        lower_input.setValue(lower)

        upper_input = DoubleInput()
        upper_input.setValue(upper)

        name_input = QtWidgets.QLineEdit()
        name_input.setText(name)
        # call the setter on a change
        name_input.textChanged.connect(issue_input.set_name)

        lower_input.valueChanged.connect(issue_input.set_lower)

        upper_input.valueChanged.connect(issue_input.set_upper)

        delete_button = QtWidgets.QPushButton('Delete')
        delete_button.clicked.connect(self.delete_row)
        delete_button.setObjectName('issue-' + str(self._row_pointer))

        self.items[issue_input.id] = issue_input

        self.add_row(name_input, lower_input, upper_input, delete_button)

        return issue_input

    def add_action(self):
        issue = self.add_issue()
        self.notify_add(issue)

    def delete_row(self):
        row = super().delete_row()

        self.notify_delete(row)


class ActorIssueBox(BoxLayout, Observer, Observable):
    """
    The ActorIssueBox is an hidden box behind the scenes, so there is a single point of truth
    """

    def add_heading(self):
        pass

    def __init__(self, actor_box: ActorBox, issue_box: IssueBox):
        super(ActorIssueBox, self).__init__('Hidden Box')
        Observable.__init__(self)

        self.actor_box = actor_box
        self.issue_box = issue_box

        self.actor_box.register(self)
        self.issue_box.register(self)

        self.items = defaultdict(lambda: dict())

        self.actors = set()
        self.issues = set()

    def clear(self):
        super(ActorIssueBox, self).clear()
        self.items = defaultdict(lambda: dict())

        self.actors = set()
        self.issues = set()

    def delete(self, observer, row):
        if observer.key == IssueBox.key:
            self.issues.remove(row)
            for actor in self.actor_box.items.values():
                item = self.items[actor.id][row.id]
                self.notify_delete(item)
                del self.items[actor.id][row.id]

        if observer.key == ActorBox.key:
            self.actors.remove(row)
            for issue in self.issue_box.items.values():
                item = self.items[row.id][issue.id]
                self.notify_delete(item)
                del self.items[row.id][issue.id]

    def add(self, observer, value):
        # if an issue is added, we need to add all the existing actors for the issue
        if observer.key == IssueBox.key:
            self.issues.add(value)
            for actor in self.actor_box.items.values():
                self.add_actor_issue(actor, value)

        # if an actor is added, we need to add all the existing issues for the actor
        if observer.key == ActorBox.key:
            self.actors.add(value)
            for issue in self.issue_box.items.values():
                self.add_actor_issue(value, issue)

        self.notify_change('redraw', True)

    def add_actor_issue(self, actor: ActorInput, issue: IssueInput, actor_issue=None):

        actor_issue_input = ActorIssueInput(actor, issue)
        actor_issue_input.id = self._row_pointer

        self.items[actor.id][issue.id] = actor_issue_input

        if actor_issue:
            actor_issue_input.set_position(str(actor_issue.issue.de_normalize(actor_issue.position)), silence=True)
            actor_issue_input.set_salience(str(actor_issue.salience), silence=True)

        self._row_pointer += 1

        self.notify_add(actor_issue_input)

    def change(self, observer, key, value):
        print('change ActorIssueBox')


class PositionSalienceBox(QtWidgets.QWidget, Observer, Observable):

    def __init__(self, actor_issue_box: ActorIssueBox):
        super(PositionSalienceBox, self).__init__()

        self.actor_issue_box = actor_issue_box
        self.actor_issue_box.register(self)

        self._row_pointer = 0

        self.choices = QtWidgets.QComboBox()
        self.choices.currentTextChanged.connect(self.redraw)

        self.container = QtWidgets.QVBoxLayout(self)
        self.container.addWidget(self.choices)

        self.grid_layout = QtWidgets.QGridLayout()
        self.grid_layout.setAlignment(QtCore.Qt.AlignTop)

        self.container.addLayout(self.grid_layout)

    def clear(self):

        self._row_pointer = 0
        clear_layout(self.grid_layout)

    def change(self, observer, key, value):
        print(key)
        if key == 'choice':
            self.update_choices()

    def delete(self, observer, actor_issue_input):
        self.redraw()
        self.update_choices()

    def add(self, observer: Observer, value):
        value.register(self)
        self.redraw()
        self.update_choices()

    def add_heading(self):
        raise NotImplementedError

    def add_row(self, *args, pointer=None):

        if pointer:
            row = pointer
        else:
            row = self._row_pointer

        for column, arg in enumerate(args):
            if isinstance(arg, str):
                arg = QtWidgets.QLabel(arg)

            self.grid_layout.addWidget(arg, row, column)

        self._row_pointer += 1

        return row

    def redraw(self):

        clear_layout(self.grid_layout)

        self.add_heading()

        for actor in self.actor_issue_box.actors:
            for issue in self.actor_issue_box.issues:

                if actor.id in self.actor_issue_box.items and issue.id in self.actor_issue_box.items[actor.id]:
                    actor_issue = self.actor_issue_box.items[actor.id][issue.id]  # type: ActorIssueInput

                    self.add_actor_issue(actor_issue)

    def add_actor_issue(self, actor_issue: ActorIssueInput):
        raise NotImplementedError

    def update_choices(self):

        self.choices.clear()

        items = [str(x.name) for x in self.actor_issue_box.issues if x != '']

        items.sort()

        self.choices.addItems(items)


class PositionBox(PositionSalienceBox):

    def add_heading(self):
        self.add_row('Actor', 'Power', 'Position')

    def add_actor_issue(self, actor_issue):
        if actor_issue.issue.name == self.choices.currentText():
            position = DoubleInput()
            position.setValue(actor_issue.position)
            position.valueChanged.connect(actor_issue.set_position)

            self.add_row(
                QtWidgets.QLabel(actor_issue.actor.name),
                QtWidgets.QLabel(str(actor_issue.actor.power)),
                position
            )


class SalienceBox(PositionSalienceBox):

    def add_heading(self):
        self.add_row('Issue', 'Power', 'Position', 'Salience')

    def add_actor_issue(self, actor_issue: ActorIssueInput):
        if actor_issue.actor.name == self.choices.currentText():
            position = DoubleInput()
            position.setValue(actor_issue.position)
            position.valueChanged.connect(actor_issue.set_position)

            salience = DoubleInput()
            salience.setValue(actor_issue.salience)
            salience.valueChanged.connect(actor_issue.set_salience)

            self.add_row(
                QtWidgets.QLabel(actor_issue.issue.name),
                QtWidgets.QLabel(str(actor_issue.actor.power)),
                position,
                salience

            )

    def update_choices(self):
        self.choices.clear()

        items = [str(x.name) for x in self.actor_issue_box.actors if x != '']
        items.sort()

        self.choices.addItems(items)


class InputWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(InputWindow, self).__init__(parent)

        self.main = QtWidgets.QHBoxLayout()
        self.left = QtWidgets.QVBoxLayout()

        self.tabs = QtWidgets.QTabWidget()

        self.actor_input_control = ActorBox()
        self.actor_input_control.add_heading()

        self.issue_input_control = IssueBox()
        self.issue_input_control.add_heading()

        self.actor_issues = ActorIssueBox(self.actor_input_control, self.issue_input_control)

        self.position_box = PositionBox(self.actor_issues)
        self.position_box.add_heading()

        self.left.addWidget(self.actor_input_control)
        self.left.addWidget(self.issue_input_control)

        self.tabs.addTab(self.position_box, 'Positions (by Issue)')

        self.salience_box = SalienceBox(self.actor_issues)
        self.salience_box.add_heading()
        self.tabs.addTab(self.salience_box, 'Saliences (by Actor)')

        self.main.addLayout(self.left)
        self.main.addWidget(self.tabs)

        q = QtWidgets.QWidget()
        q.setLayout(self.main)

        menubar = QtWidgets.QMenuBar()
        self.setMenuBar(menubar)

        file_menu = menubar.addMenu('File')
        example_menu = menubar.addMenu('Examples')

        load_kopenhagen = QtWidgets.QAction('&load Kopenhagen', menubar)
        load_kopenhagen.triggered.connect(self.load_kopenhagen)

        open_action = QtWidgets.QAction('Open', menubar)
        open_action.triggered.connect(self.open_dialog)

        save_action = QtWidgets.QAction('Save', menubar)
        save_action.triggered.connect(self.save_location)

        example_menu.addAction(load_kopenhagen)

        file_menu.addAction(open_action)
        file_menu.addAction(save_action)

        self.setCentralWidget(q)

        self.setGeometry(300, 300, 1024, 768)
        self.setWindowTitle('Decide Exchange Model')
        self.show()

    def load_kopenhagen(self):
        self.load(data_file_path('kopenhagen'))

    def open_dialog(self):

        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select input data")

        if file_name:
            self.load(file_name)

    def save_location(self):
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Select input data")

        if file_name:
            self.save(file_name)

    def load(self, input_filename):

        model = init_model('equal', input_filename, p=0.0)

        csv_parser = csvparser.CsvParser(model)
        csv_parser.read(input_filename)

        actor_inputs = {}

        self.actor_input_control.clear()
        self.issue_input_control.clear()
        self.actor_issues.clear()
        self.position_box.clear()
        self.salience_box.clear()

        for issue, actor_issues in model.actor_issues.items():
            issue_input = self.issue_input_control.add_issue(issue.name, issue.lower, issue.upper)

            self.actor_issues.issues.add(issue_input)

            for actor, actor_issue in actor_issues.items():
                if actor not in actor_inputs:
                    actor_issue = actor_issue  # type: ActorIssue
                    actor_input = self.actor_input_control.add_actor(actor.name, actor_issue.power)
                    actor_inputs[actor] = actor_input

                    self.actor_issues.actors.add(actor_input)
                else:
                    actor_input = actor_inputs[actor]

                self.actor_issues.add_actor_issue(actor_input, issue_input, actor_issue)

        self.position_box.redraw()

    def save(self, filename):
        with open(filename, 'w') as file:

            for actor in self.actor_input_control.items.values():
                file.write(';'.join(['#A', actor.name, os.linesep]))

            for issue in self.issue_input_control.items.values():
                file.write(';'.join(['#P', issue.name, str(issue.lower), str(issue.upper), os.linesep]))

            for actor_id, actor_issues in self.actor_issues.items.items():

                for issue_id, actor_issue in actor_issues.items():
                    actor_issue = actor_issue  # type: ActorIssueInput

                    file.write(';'.join(
                        ['#M', actor_issue.actor.name, actor_issue.issue.name, str(actor_issue.position),
                         str(actor_issue.salience), str(actor_issue.power), os.linesep]))

        open_file(filename)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    try:
        ex = InputWindow()

        sys.exit(app.exec_())
    except:
        print('catch')


if __name__ == '__main__':
    main()