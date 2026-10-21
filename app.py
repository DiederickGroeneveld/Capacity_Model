from capacity_model.config import get_settings
from capacity_model.ui.pages import render_home_page


settings = get_settings()


def main() -> None:
    render_home_page(settings)


if __name__ == "__main__":
    main()
