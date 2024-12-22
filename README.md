# TaskManager_tgbot
Task Manager Telegram Bot

Overview

This project is a Telegram bot designed to help users manage tasks efficiently. It allows users to create tasks, view their list of tasks, delete tasks, and receive deadline reminders.

Key Features
	•	Task Creation: Users can add tasks by specifying a name, deadline, and description.
	•	Task Viewing: Users can view all their tasks, along with details like deadlines and descriptions.
	•	Task Deletion: Users can delete tasks by entering the task’s unique ID.
	•	Reminders: The bot sends reminders:
	•	1 day before the task deadline.
	•	2 hours before the task deadline.

Technologies Used
	•	Python: The primary programming language.
	•	Aiogram: For Telegram bot framework.
	•	APScheduler: For scheduling reminders.
	•	SQLite: To store user tasks.
	•	Logging: For tracking application events and errors.

How It Works
	1.	Main Menu: Provides options to add tasks or view existing tasks.
	2.	Task States: Tracks user interaction states (e.g., adding task name, deadline, or description).
	3.	Scheduler: Handles timed notifications for upcoming deadlines.
	4.	Database: Stores tasks persistently using the db_taskmanager module.
