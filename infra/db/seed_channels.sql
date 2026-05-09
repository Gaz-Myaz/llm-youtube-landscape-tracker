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
  ('UCbfYPyITQ-7l4upoX8nvctg', 'Two Minute Papers', '@TwoMinutePapers', 'Research-focused AI and machine learning explainers.', 'https://www.youtube.com/@TwoMinutePapers', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg', 'en'),
  ('UCSHZKyawb77ixDdsGog4iWA', 'Lex Fridman', '@lexfridman', 'Long-form technical interviews with AI researchers and builders.', 'https://www.youtube.com/@lexfridman', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCSHZKyawb77ixDdsGog4iWA', 'en'),
  ('UCsBjURrPoezykLs9EqgamOA', 'Fireship', '@Fireship', 'Fast software engineering and AI tooling explainers.', 'https://www.youtube.com/@Fireship', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCsBjURrPoezykLs9EqgamOA', 'en'),
  ('UCUyeluBRhGPCW4rPe_UvBZQ', 'ThePrimeTime', '@ThePrimeagen', 'Developer commentary, tools, and AI coding workflow coverage.', 'https://www.youtube.com/@ThePrimeagen', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCUyeluBRhGPCW4rPe_UvBZQ', 'en'),
  ('UC8butISFwT-Wl7EV0hUK0BQ', 'freeCodeCamp.org', '@freecodecamp', 'Technical courses and tutorials, including practical AI application development.', 'https://www.youtube.com/@freecodecamp', 'https://www.youtube.com/feeds/videos.xml?channel_id=UC8butISFwT-Wl7EV0hUK0BQ', 'en'),
  ('UCawZsQWqfGSbCI5yjkdVkTA', 'Matthew Berman', '@matthew_berman', 'Frequent AI model, tooling, and local LLM coverage with practical demos.', 'https://www.youtube.com/@matthew_berman', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCawZsQWqfGSbCI5yjkdVkTA', 'en'),
  ('UCZHmQk67mSJgfCCTn7xBfew', 'Yannic Kilcher', '@YannicKilcher', 'Research-heavy coverage of machine learning papers, model releases, and AI systems.', 'https://www.youtube.com/@YannicKilcher', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCZHmQk67mSJgfCCTn7xBfew', 'en'),
  ('UCNJ1Ymd5yFuUPtn21xtRbbw', 'AI Explained', '@AIExplained-official', 'Accessible analysis of frontier models, agents, local inference, and open-weight AI.', 'https://www.youtube.com/@AIExplained-official', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCNJ1Ymd5yFuUPtn21xtRbbw', 'en'),
  ('UCqcbQf6yw5KzRoDDcZ_wBSw', 'Wes Roth', '@WesRoth', 'AI product, model release, and ecosystem commentary focused on real-world impact.', 'https://www.youtube.com/@WesRoth', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCqcbQf6yw5KzRoDDcZ_wBSw', 'en'),
  ('UCXZCJLdBC09xxGZ6gcdrc6A', 'OpenAI', '@OpenAI', 'Official OpenAI updates, model demos, product launches, and research announcements.', 'https://www.youtube.com/@OpenAI', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCXZCJLdBC09xxGZ6gcdrc6A', 'en'),
  ('UCP7jMXSY2xbc3KCAE0MHQ-A', 'Google DeepMind', '@GoogleDeepMind', 'Research and product coverage from Google DeepMind across frontier AI systems.', 'https://www.youtube.com/@GoogleDeepMind', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCP7jMXSY2xbc3KCAE0MHQ-A', 'en'),
  ('UCcIXc5mJsHVYTZR1maL5l9w', 'DeepLearningAI', '@Deeplearningai', 'AI education, applied LLM development, agents, and machine learning course material.', 'https://www.youtube.com/@Deeplearningai', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCcIXc5mJsHVYTZR1maL5l9w', 'en'),
  ('UCC-lyoTfSrcJzA1ab3APAgw', 'LangChain', '@LangChain', 'Developer-focused LLM application, agent, retrieval, and production workflow coverage.', 'https://www.youtube.com/@LangChain', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCC-lyoTfSrcJzA1ab3APAgw', 'en'),
  ('UCm5UKq2ziKyx4mlYmcqjo4Q', 'Droiderru', '@Droiderru', 'Russian-language technology and AI product coverage.', 'https://www.youtube.com/@Droiderru', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCm5UKq2ziKyx4mlYmcqjo4Q', 'ru')
on conflict (youtube_channel_id) do update set
  title = excluded.title,
  handle = excluded.handle,
  description = excluded.description,
  url = excluded.url,
  rss_url = excluded.rss_url,
  language = excluded.language,
  updated_at = now();
