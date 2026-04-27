# Attribution & Third-Party Credits

## Machine Learning Models

| Model | Source | License |
|-------|--------|---------|
| CLIP ViT-B/32 | [openai/clip-vit-base-patch32](https://huggingface.co/openai/clip-vit-base-patch32) on HuggingFace — active zero-shot classifier | MIT |
| EfficientNet-B3 | [torchvision](https://pytorch.org/vision/stable/models/efficientnet.html) — ImageNet-pretrained weights (used in training script) | BSD-3-Clause |
| all-MiniLM-L6-v2 | [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) on HuggingFace — Duke menu semantic matching | Apache 2.0 |
| transformers | [HuggingFace Transformers](https://github.com/huggingface/transformers) — CLIP model loading | Apache 2.0 |

## Datasets

| Dataset | Source | License |
|---------|--------|---------|
| Food-101 | Bossard et al., ECCV 2014 — [ETH Zürich](https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/) | Unknown / research use |
| Duke Nutrition Data | [Duke Net Nutrition (CBORD)](https://netnutrition.cbord.com/nn-prod/Duke#) | Public dining info |

## Backend Libraries

| Library | Purpose | License |
|---------|---------|---------|
| [FastAPI](https://fastapi.tiangolo.com/) | Web framework | MIT |
| [SQLAlchemy](https://www.sqlalchemy.org/) | ORM / SQLite | MIT |
| [python-jose](https://github.com/mpdavis/python-jose) | JWT signing | MIT |
| [bcrypt](https://pypi.org/project/bcrypt/) | Password hashing (direct bcrypt, passlib incompatible with bcrypt≥4) | Apache 2.0 |
| [sentence-transformers](https://www.sbert.net/) | Semantic text embeddings | Apache 2.0 |
| [PyTorch](https://pytorch.org/) | Deep learning framework | BSD-3-Clause |
| [torchvision](https://pytorch.org/vision/) | Vision models & transforms | BSD-3-Clause |
| [Pillow](https://python-pillow.org/) | Image I/O | HPND |
| [pandas](https://pandas.pydata.org/) | Nutrition DB handling | BSD-3-Clause |
| [selenium](https://www.selenium.dev/) | Headless Chrome for CBORD Net Nutrition scraping | Apache 2.0 |
| [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) | HTML parsing of nutrition dialogs | MIT |
| [requests](https://requests.readthedocs.io/) | HTTP client | Apache 2.0 |
| [uvicorn](https://www.uvicorn.org/) | ASGI server | BSD-3-Clause |

## Frontend Libraries

| Library | Purpose | License |
|---------|---------|---------|
| [React](https://react.dev/) | UI framework | MIT |
| [Vite](https://vitejs.dev/) | Build tool | MIT |
| [Tailwind CSS](https://tailwindcss.com/) | Utility-first CSS | MIT |
| [React Router](https://reactrouter.com/) | Client-side routing | MIT |
| [@tanstack/react-query](https://tanstack.com/query) | Server state management | MIT |
| [Recharts](https://recharts.org/) | Chart components | MIT |
| [axios](https://axios-http.com/) | HTTP client | MIT |

## Acknowledgements

This project was built as part of **CS 372** at Duke University.
The pipeline design is informed by the companion notebook
`notebooks/duke_macro_tracker_skeleton.ipynb` included in this repository.
As for AI use, I used Claude to help build out a working frontend and debug problems within notebook skeleton.