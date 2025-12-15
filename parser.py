import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class SurveyJSONSplitter:
    """
    Parses survey payload and splits it into separate JSON files by section.
    Creates 4 files: site_details.json, location.json, site_photos.json, 
    and repeat_records.json (consolidated all repeat types with single-line details).
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize the splitter.
        
        Args:
            output_dir: Directory to save output files (default: 'output')
        """
        self.output_dir = output_dir
        
        # Priority fields to extract from repeat records (if they exist)
        self.priority_fields = {
            'issue', 'issues', 'description', 'note', 'notes', 
            'type', 'types', 'context', 'severity', 'status',
            'height', 'heights', 'location', 'locations'
        }
        
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
            'weather_api_key', 'weather_json',
            'creationdate', 'editdate', 'creator', 'editor'
        }
        
        for key, value in attrs.items():
            # Skip excluded fields
            if key.lower() in exclude_fields:
                continue
            
            # Skip null/empty values
            if value is None or value == "":
                continue
            
            # Format timestamps
            if 'datetime' in key.lower():
                formatted = self._format_timestamp(value)
                if formatted:
                    cleaned[key] = formatted
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _extract_priority_attributes_as_string(self, attrs: Dict[str, Any]) -> str:
        """
        Extract priority fields and format as single-line string.
        Example: "location: leg_a, issue: Feedline not secured, severity: 3"
        """
        priority_data = []
        
        for key, value in attrs.items():
            key_lower = key.lower()
            
            # Check if this is a priority field
            if any(priority in key_lower for priority in self.priority_fields):
                # Skip if empty
                if value is None or value == "":
                    continue
                
                # Format timestamps if needed
                if 'datetime' in key_lower:
                    formatted = self._format_timestamp(value)
                    if formatted:
                        priority_data.append(f"{key}: {formatted}")
                else:
                    priority_data.append(f"{key}: {value}")
        
        return ", ".join(priority_data) if priority_data else ""
    
    def _extract_apex_height(self, attrs: Dict[str, Any]) -> Optional[Any]:
        """Extract apex_height from attributes if it exists"""
        return attrs.get('apex_height')
    
    def _extract_site_details(self, attrs: Dict[str, Any], customer_site_id: str, 
                             survey_type: str, apex_height: Optional[Any]) -> Dict[str, Any]:
        """Create site_details.json content"""
        cleaned_attrs = self._clean_attributes(attrs)
        
        metadata = {
            "section_type": "site_details",
            "customer_site_id": customer_site_id,
            "survey_type": survey_type
        }
        
        # Add apex_height to metadata if it exists
        if apex_height is not None:
            metadata["apex_height"] = apex_height
        
        return {
            "metadata": metadata,
            "data": cleaned_attrs
        }
    
    def _extract_location(self, geometry: Dict[str, Any], customer_site_id: str, survey_type: str) -> Dict[str, Any]:
        """Create location.json content"""
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
        photos_by_category = []
        total_photos = 0
        
        if attachments:
            for category, files in attachments.items():
                if files:
                    photos_by_category.append({
                        "category": category,
                        "photo_count": len(files)
                    })
                    total_photos += len(files)
        
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
    
    def _extract_all_repeat_records(self, repeats: Dict[str, List[Dict]], 
                                    customer_site_id: str, survey_type: str,
                                    apex_height: Optional[Any]) -> Dict[str, Any]:
        """
        Create consolidated repeat_records.json with single-line details format.
        Format: 
        {
          "record_type": "TIA Infos",
          "total_records": 8,
          "total_photos": 24,
          "records": [
            {"record_1": {"photo_count": 3, "details": "location: leg_a, issue: Feedline not secured, severity: 3"}},
            {"record_2": {...}}
          ]
        }
        """
        all_record_types = []
        total_records_overall = 0
        total_photos_overall = 0
        
        for table_name, records in repeats.items():
            if not records:
                continue
            
            type_photo_count = 0
            type_records = []
            
            for i, record in enumerate(records, 1):
                attrs = record.get('attributes', {})
                
                # Extract priority fields as single-line string
                details_string = self._extract_priority_attributes_as_string(attrs)
                
                # Count photos (no names, no URLs)
                photo_count = 0
                if 'attachments' in record and record['attachments']:
                    for category, files in record['attachments'].items():
                        if files:
                            photo_count += len(files)
                
                type_photo_count += photo_count
                
                # Build individual record with single-line format
                record_data = {
                    "photo_count": photo_count
                }
                
                # Add details string if there are any priority attributes
                if details_string:
                    record_data["details"] = details_string
                
                # Format: {"record_1": {...}, "record_2": {...}}
                type_records.append({f"record_{i}": record_data})
            
            total_records_overall += len(records)
            total_photos_overall += type_photo_count
            
            # Create summary structure for this record type
            record_type_summary = {
                "record_type": table_name,
                "total_records": len(records),
                "total_photos": type_photo_count,
                "records": type_records
            }
            
            all_record_types.append(record_type_summary)
        
        metadata = {
            "section_type": "repeat_records",
            "customer_site_id": customer_site_id,
            "survey_type": survey_type,
            "total_record_types": len(all_record_types),
            "total_records": total_records_overall,
            "total_photos": total_photos_overall
        }
        
        # Add apex_height to metadata if it exists
        if apex_height is not None:
            metadata["apex_height"] = apex_height
        
        return {
            "metadata": metadata,
            "data": {
                "record_types": all_record_types
            }
        }
    
    def split_and_save(self, survey_data: Dict[str, Any], output_dir: str = None) -> Dict[str, Any]:
        """
        Split survey data into 4 separate JSON files.
        
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
        apex_height = self._extract_apex_height(attrs)
        
        files_created = []
        
        # 1. Create site_details.json
        site_details = self._extract_site_details(attrs, customer_site_id, survey_type, apex_height)
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
        
        # 4. Create single consolidated repeat_records.json
        if 'repeats' in feature and feature['repeats']:
            repeat_records = self._extract_all_repeat_records(
                feature['repeats'],
                customer_site_id,
                survey_type,
                apex_height
            )
            
            repeat_file = os.path.join(self.output_dir, 'repeat_records.json')
            with open(repeat_file, 'w', encoding='utf-8') as f:
                json.dump(repeat_records, f, indent=2, ensure_ascii=False)
            
            files_created.append('repeat_records.json')
        
        summary = {
            'status': 'success',
            'output_directory': self.output_dir,
            'files_created': files_created,
            'total_files': len(files_created),
            'customer_site_id': customer_site_id,
            'survey_type': survey_type
        }
        
        if apex_height is not None:
            summary['apex_height'] = apex_height
        
        print(f"\nSuccessfully split survey data into {len(files_created)} files")
        print(f"Output directory: {self.output_dir}")
        print(f"\nFiles created:")
        for file in files_created:
            print(f"  - {file}")
        
        return summary
    
    def split_from_file(self, filepath: str, output_dir: str = None) -> Dict[str, Any]:
        """
        Split survey data from a JSON file into 4 separate JSON files.
        
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