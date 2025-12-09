import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class SurveyJSONSplitter:
    """
    Parses survey payload and splits it into separate JSON files by section.
    Creates 4+ files: site_details.json, location.json, site_photos.json, 
    and one file per repeat record type.
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize the splitter.
        
        Args:
            output_dir: Directory to save output files (default: 'output')
        """
        self.output_dir = output_dir
        
    def _format_timestamp(self, unix_ms: Any) -> str:
        """Convert Unix millisecond timestamp to readable date"""
        try:
            if unix_ms and unix_ms != 'N/A':
                dt_obj = datetime.fromtimestamp(int(unix_ms) / 1000)
                return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError, OSError):
            pass
        return None
    
    def _create_output_dir(self) -> str:
        """Create output directory if it doesn't exist"""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        return self.output_dir
    
    def _clean_attributes(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Remove null/empty values and unwanted fields from attributes"""
        cleaned = {}
        
        # Fields to exclude
        exclude_fields = {
            'objectid', 'globalid', 'parentglobalid',
            'organization_url', 'organization_id', 'confirm_org',
            'customer', 'customer_other',
            'flag_survey_bin', 'flag_comment',
            'weather_api_key', 'weather_json'
        }
        
        for key, value in attrs.items():
            # Skip excluded fields
            if key.lower() in exclude_fields:
                continue
            
            # Skip null/empty values
            if value is None or value == "":
                continue
            
            # Format timestamps
            if 'datetime' in key.lower() or key.lower() in ['creationdate', 'editdate']:
                formatted = self._format_timestamp(value)
                if formatted:
                    cleaned[key] = formatted
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _extract_site_details(self, attrs: Dict[str, Any], customer_site_id: str, survey_type: str) -> Dict[str, Any]:
        """Create site_details.json content"""
        processing_time = datetime.now().isoformat() + 'Z'
        
        # Clean all attributes
        cleaned_attrs = self._clean_attributes(attrs)
        
        return {
            "metadata": {
                "section_type": "site_details",
                "customer_site_id": customer_site_id,
                "survey_type": survey_type
            },
            "data": cleaned_attrs
        }
    
    def _extract_location(self, geometry: Dict[str, Any], customer_site_id: str, survey_type: str) -> Dict[str, Any]:
        """Create location.json content"""
        processing_time = datetime.now().isoformat() + 'Z'
        
        location_data = {}
        if geometry:
            location_data = {
                "latitude": geometry.get('y'),
                "longitude": geometry.get('x'),
                "spatial_reference": geometry.get('spatialReference', {}).get('wkid')
            }
        
        return {
            "metadata": {
                "section_type": "location",
                "customer_site_id": customer_site_id,
                "survey_type": survey_type
            },
            "data": location_data
        }
    
    def _extract_site_photos(self, attachments: Dict[str, List[Dict]], customer_site_id: str, survey_type: str) -> Dict[str, Any]:
        """Create site_photos.json content"""
        processing_time = datetime.now().isoformat() + 'Z'
        
        photos_by_category = []
        total_photos = 0
        
        if attachments:
            for category, files in attachments.items():
                if files:
                    filenames = [file.get('name', 'Unknown') for file in files]
                    photos_by_category.append({
                        "category": category,
                        "photo_count": len(filenames),
                        "files": filenames
                    })
                    total_photos += len(filenames)
        
        return {
            "metadata": {
                "section_type": "site_photos",
                "customer_site_id": customer_site_id,
                "survey_type": survey_type,
                "total_photos": total_photos,
                "total_categories": len(photos_by_category)
            },
            "data": {
                "photos_by_category": photos_by_category
            }
        }
    
    def _extract_repeat_record_type(self, table_name: str, records: List[Dict], 
                                    customer_site_id: str, survey_type: str) -> Dict[str, Any]:
        """Create repeat_records_[type].json content"""
        processing_time = datetime.now().isoformat() + 'Z'
        
        formatted_records = []
        total_photos = 0
        
        for i, record in enumerate(records, 1):
            attrs = record.get('attributes', {})
            cleaned_attrs = self._clean_attributes(attrs)
            
            # Process attachments
            attachments_data = {
                "count": 0,
                "files": []
            }
            
            if 'attachments' in record and record['attachments']:
                for category, files in record['attachments'].items():
                    if files:
                        for file in files:
                            attachments_data["files"].append({
                                "field_name": category,
                                "filename": file.get('name', 'Unknown')
                            })
                        attachments_data["count"] += len(files)
                        total_photos += len(files)
            
            formatted_record = {
                "record_number": i
            }
            
            # Add attributes if present
            if cleaned_attrs:
                formatted_record["attributes"] = cleaned_attrs
            
            # Add attachments
            formatted_record["attachments"] = attachments_data
            
            formatted_records.append(formatted_record)
        
        return {
            "metadata": {
                "section_type": "repeat_records",
                "record_type": table_name,
                "customer_site_id": customer_site_id,
                "survey_type": survey_type,
                "total_records": len(formatted_records),
                "total_photos": total_photos
            },
            "data": {
                "records": formatted_records
            }
        }
    
    def split_and_save(self, survey_data: Dict[str, Any], output_dir: str = None) -> Dict[str, Any]:
        """
        Split survey data into separate JSON files.
        
        Args:
            survey_data: The complete survey JSON payload
            output_dir: Optional override for output directory
            
        Returns:
            Dict containing summary of files created
        """
        if output_dir:
            self.output_dir = output_dir
        
        # Create output directory
        self._create_output_dir()
        
        feature = survey_data.get('feature', {})
        
        if not feature:
            return {'error': 'No feature data found in payload'}
        
        attrs = feature.get('attributes', {})
        customer_site_id = attrs.get('customer_site_id', 'unknown')
        survey_type = attrs.get('survey_type', 'unknown')
        
        files_created = []
        
        # 1. Create site_details.json
        site_details = self._extract_site_details(attrs, customer_site_id, survey_type)
        site_details_file = os.path.join(self.output_dir, 'site_details.json')
        with open(site_details_file, 'w', encoding='utf-8') as f:
            json.dump(site_details, f, indent=2, ensure_ascii=False)
        files_created.append('site_details.json')
        
        # 2. Create location.json
        location = self._extract_location(feature.get('geometry', {}), customer_site_id, survey_type)
        location_file = os.path.join(self.output_dir, 'location.json')
        with open(location_file, 'w', encoding='utf-8') as f:
            json.dump(location, f, indent=2, ensure_ascii=False)
        files_created.append('location.json')
        
        # 3. Create site_photos.json
        site_photos = self._extract_site_photos(
            feature.get('attachments', {}), 
            customer_site_id, 
            survey_type
        )
        site_photos_file = os.path.join(self.output_dir, 'site_photos.json')
        with open(site_photos_file, 'w', encoding='utf-8') as f:
            json.dump(site_photos, f, indent=2, ensure_ascii=False)
        files_created.append('site_photos.json')
        
        # 4. Create repeat_records_[type].json for each record type
        if 'repeats' in feature and feature['repeats']:
            for table_name, records in feature['repeats'].items():
                if records:
                    repeat_data = self._extract_repeat_record_type(
                        table_name, 
                        records, 
                        customer_site_id, 
                        survey_type
                    )
                    
                    # Clean filename: lowercase, replace spaces/special chars with underscore
                    safe_table_name = table_name.lower().replace(' ', '_').replace('/', '_')
                    repeat_file = os.path.join(
                        self.output_dir, 
                        f'repeat_records_{safe_table_name}.json'
                    )
                    
                    with open(repeat_file, 'w', encoding='utf-8') as f:
                        json.dump(repeat_data, f, indent=2, ensure_ascii=False)
                    
                    files_created.append(f'repeat_records_{safe_table_name}.json')
        
        summary = {
            'status': 'success',
            'output_directory': self.output_dir,
            'files_created': files_created,
            'total_files': len(files_created),
            'customer_site_id': customer_site_id,
            'survey_type': survey_type
        }
        
        print(f"\n✓ Successfully split survey data into {len(files_created)} files")
        print(f"✓ Output directory: {self.output_dir}")
        print(f"\nFiles created:")
        for file in files_created:
            print(f"  - {file}")
        
        return summary
    
    def split_from_file(self, filepath: str, output_dir: str = None) -> Dict[str, Any]:
        """
        Split survey data from a JSON file into separate JSON files.
        
        Args:
            filepath: Path to the input JSON file
            output_dir: Optional override for output directory
            
        Returns:
            Dict containing summary of files created
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                survey_data = json.load(f)
            
            return self.split_and_save(survey_data, output_dir)
                
        except FileNotFoundError:
            return {'error': f'File not found: {filepath}'}
        except json.JSONDecodeError as e:
            return {'error': f'Invalid JSON: {str(e)}'}
        except Exception as e:
            return {'error': f'Error processing file: {str(e)}'}

if __name__ == "__main__":
    splitter = SurveyJSONSplitter(output_dir="output")

    result = splitter.split_from_file('20251023205622_1450 Experiment Farm Rd_US632993_Structure Climb Inspection.json')
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"\nSplit complete!")
        print(f"Customer Site ID: {result['customer_site_id']}")
        print(f"Survey Type: {result['survey_type']}")
        print(f"Total files created: {result['total_files']}")