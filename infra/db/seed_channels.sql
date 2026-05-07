insert into topics (slug, label, description) values
  ('agents', 'AI Agents', 'Agentic workflows, tool use, planning, and autonomous AI systems.'),
  ('rag', 'RAG', 'Retrieval augmented generation and knowledge-grounded applications.'),
  ('evals', 'Evaluation', 'Model and system evaluation methods, tests, and benchmarks.'),
  ('benchmarks', 'Benchmarks', 'Performance comparisons, leaderboards, and benchmark interpretation.'),
  ('coding-assistants', 'Coding Assistants', 'AI coding tools, software engineering agents, and developer workflows.'),
  ('open-source-models', 'Open Source Models', 'Open-weight and community model releases.'),
  ('local-inference', 'Local Inference', 'Running LLMs locally or on private infrastructure.'),
  ('multimodal', 'Multimodal', 'Text, image, audio, and video model capabilities.'),
  ('fine-tuning', 'Fine Tuning', 'Training, adaptation, LoRA, and customization.'),
  ('safety-alignment', 'Safety and Alignment', 'Risk, alignment, policy, and safety discussions.'),
  ('enterprise-adoption', 'Enterprise Adoption', 'LLM deployment patterns for companies and teams.'),
  ('model-releases', 'Model Releases', 'New model announcements and release analysis.')
on conflict (slug) do update set
  label = excluded.label,
  description = excluded.description;

insert into channels (youtube_channel_id, title, handle, description, url, rss_url, language) values
  ('UC2D2CMWXMOVWx7giW1n3LIg', 'Two Minute Papers', '@TwoMinutePapers', 'Research-focused AI and machine learning explainers.', 'https://www.youtube.com/@TwoMinutePapers', 'https://www.youtube.com/feeds/videos.xml?channel_id=UC2D2CMWXMOVWx7giW1n3LIg', 'en'),
  ('UCSHZKyawb77ixDdsGog4iWA', 'Lex Fridman', '@lexfridman', 'Long-form technical interviews with AI researchers and builders.', 'https://www.youtube.com/@lexfridman', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCSHZKyawb77ixDdsGog4iWA', 'en'),
  ('UCbfYPyITQ-7l4upoX8nvctg', 'Fireship', '@Fireship', 'Fast software engineering and AI tooling explainers.', 'https://www.youtube.com/@Fireship', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg', 'en'),
  ('UCUyeluBRhGPCW4rPe_UvBZQ', 'ThePrimeTime', '@ThePrimeTimeagen', 'Developer commentary, tools, and AI coding workflow coverage.', 'https://www.youtube.com/@ThePrimeTimeagen', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCUyeluBRhGPCW4rPe_UvBZQ', 'en'),
  ('UC8butISFwT-Wl7EV0hUK0BQ', 'freeCodeCamp.org', '@freecodecamp', 'Technical courses and tutorials, including practical AI application development.', 'https://www.youtube.com/@freecodecamp', 'https://www.youtube.com/feeds/videos.xml?channel_id=UC8butISFwT-Wl7EV0hUK0BQ', 'en')
on conflict (youtube_channel_id) do update set
  title = excluded.title,
  handle = excluded.handle,
  description = excluded.description,
  url = excluded.url,
  rss_url = excluded.rss_url,
  language = excluded.language,
  updated_at = now();
