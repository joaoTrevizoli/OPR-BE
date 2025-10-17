include .env
export

run:
	echo Running
	WATCHFILES_FORCE_POLLING=1 uvicorn main:app --reload --reload-exclude ".git/*" --reload-exclude ".venv/*" --reload-exclude "__pycache__/*"
