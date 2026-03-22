## Execution Efficiency

### Use of agents 
- Use the minimum amount of agents possible in parallel to conserve usage during the 5-hour session limit, even if the work takes longer. 

### File reading
- To inspect a known section of a large file, use grep to find the line
  number then sed -n 'N,Mp' to read only those lines. Do not cat files
  over 200 lines unless the full content is required.
- To confirm a file was written successfully, print the filename and
  character count only. Do not preview output files unless asked.

### Syntax validation
- After writing or modifying any Python file, run
  python3 -m py_compile <filename> before executing it.
- Test any new regex pattern in isolation with
  python3 -c "import re; re.compile(r'<pattern>')"
  before embedding it in source.

### Pipeline execution
- The M2 pipeline (M2_batch_runner → validate_extractions →
  map_study_coverage) produces stable output files committed to the repo.
  Do not re-run the pipeline unless a prompt explicitly modifies a parser
  or extractor .py file. If a prompt only reads output JSONs, use the
  existing files.
- When running pipeline scripts, suppress INFO-level log output with
  2>/dev/null unless the logs are needed for diagnosis.

### Output verbosity
- Do not print JSON objects or large data structures inline. Use slices:
  list(data.items())[:3] or data['key'] for targeted inspection.
- For batch/pipeline runs, print only the final summary line, not
  per-drug progress lines.

### Verification
- Consolidate verification: apply all edits for a prompt, then run a
  single verification pass, rather than verifying after each individual
  change.

### Session boundaries
- Each prompt that ends with a git commit is a natural session boundary.
  If context is running low, commit and note "continue in next session."
  Do not batch work from multiple prompts into a single commit.
  
  