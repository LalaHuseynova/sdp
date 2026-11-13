tell application "Microsoft PowerPoint"
 open POSIX file "/Users/ulkerhuseynova/Desktop/SAFE-Mem/output/pptx/safemem_research_20261101_v2/source/review_pass2.pptx"
 set p to active presentation
 save p in POSIX file "/Users/ulkerhuseynova/Desktop/SAFE-Mem/output/pptx/safemem_research_20261101_v2/source/pass2.pptx" as save as Open XML presentation
 save p in POSIX file "/Users/ulkerhuseynova/Desktop/SAFE-Mem/output/pptx/safemem_research_20261101_v2/source/pass2.pdf" as save as PDF
 return {name of p, count of slides of p}
end tell
