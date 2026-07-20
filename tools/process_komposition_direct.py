#!/usr/bin/env python3
"""
Direct komposition processing test
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from src.server import process_komposition_file

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    komposition_path = "subnautic_music_video_komposition.json"
    
    if not Path(komposition_path).exists():
        logger.error(f"Komposition file not found: {komposition_path}")
        return
    
    logger.info(f"🔄 Processing komposition: {komposition_path}")
    
    try:
        result = await process_komposition_file(komposition_path)
        logger.info(f"✅ Processing completed successfully")
        
        # Save result
        result_path = Path("processing_result.json")
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        logger.info(f"📋 Result saved: {result_path}")
        
        if 'output_path' in result:
            output_path = result['output_path']
            if Path(output_path).exists():
                logger.info(f"🎥 Video created: {output_path}")
                file_size = Path(output_path).stat().st_size
                logger.info(f"   Size: {file_size / 1024 / 1024:.1f} MB")
            else:
                logger.warning(f"⚠️ Output file not found: {output_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(main())