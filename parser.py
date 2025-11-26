import json
from datetime import datetime
from typing import Dict, List, Any, Optional


class SurveyParser:
    """
    Parses survey payload and extracts important feature data without chunking.
    Focuses on extracting and formatting key information in a clean, readable format.
    """
    
    def __init__(self, excluded_fields: Optional[List[str]] = None):
        """
        Initialize the parser with optional field exclusions.
        
        Args:
            excluded_fields: List of field names to exclude from output
        """
        # Built-in exclusions for noisy/irrelevant fields
        self.auto_exclude = {
            'organization_url', 'organization_id', 'confirm_org',
            'customer', 'customer_other',
            'flag_survey_bin', 'flag_comment',
            'member_lookup',
            'weather_api_key', 'weather_json',
            'objectid', 'globalid', 'parentglobalid'
        }
        
        # Add user-provided exclusions
        if excluded_fields:
            self.auto_exclude.update(field.lower() for field in excluded_fields)
    
    def _format_timestamp(self, unix_ms: Any) -> str:
        """Convert Unix millisecond timestamp to readable date"""
        try:
            if unix_ms and unix_ms != 'N/A':
                dt_obj = datetime.fromtimestamp(int(unix_ms) / 1000)
                return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError, OSError):
            pass
        return 'N/A'
    
    def _should_include_field(self, key: str, value: Any) -> bool:
        """Determine if a field should be included in output"""
        key_lower = key.lower()
        
        # Exclude if in exclusion list
        if key_lower in self.auto_exclude:
            return False
        
        # Exclude count/index fields
        if key_lower.endswith(('_count', '_index', '_idx')):
            return False
        
        # Exclude empty values
        if value is None or value == "":
            return False
        
        return True
    
    def _format_attributes(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and format important attributes"""
        formatted = {}
        
        for key, value in attrs.items():
            if not self._should_include_field(key, value):
                continue
            
            # Format timestamp fields
            if 'datetime' in key.lower() or 'date' in key.lower():
                formatted[key] = self._format_timestamp(value)
            else:
                formatted[key] = value
        
        return formatted
    
    def _extract_site_info(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Extract core site identification information"""
        site_info = {
            'customer_site_id': attrs.get('customer_site_id', 'N/A'),
            'customer_site_name': attrs.get('customer_site_name', 'N/A'),
            'customer_label': attrs.get('customer_label', 'N/A'),
            'survey_type': attrs.get('survey_type', 'N/A'),
            'structure_type': attrs.get('structure_type', 'N/A'),
            'site_visit_datetime': self._format_timestamp(attrs.get('site_visit_datetime')),
        }
        
        # Add any other important top-level fields
        priority_fields = [
            'username', 'survey_purpose', 'inspection_technician',
            'email','apex_height', 'structure_steel_height'
        ]
        
        for field in priority_fields:
            if field in attrs and self._should_include_field(field, attrs[field]):
                site_info[field] = attrs[field]
        
        return site_info
    
    def _extract_location(self, geometry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract location/geometry information"""
        if not geometry:
            return {}
        
        return {
            'latitude': geometry.get('y', 'N/A'),
            'longitude': geometry.get('x', 'N/A'),
            'spatial_reference': geometry.get('spatialReference', {}).get('wkid', 'N/A')
        }
    
    def _format_record(self, record: Dict[str, Any], record_num: int) -> Dict[str, Any]:
        """Format a single repeat record with important attributes"""
        attrs = record.get('attributes', {})
        
        # Priority attributes for records (most important first)
        priority_keys = [
            'severity', 'tia_severity',
            'location', 'tia_location',
            'issue', 'tia_issue', 'tia_label',
            'identifier', 'tia_identifier_label', 'tia_def_identifier',
            'notes', 'tia_notes', 'description', 'name',
            'height', 'width', 'length', 'type', 'route'
        ]
        
        formatted_record = {'record_number': record_num}
        
        # First pass: get priority attributes
        for priority_key in priority_keys:
            for key, value in attrs.items():
                if (key.lower() == priority_key.lower() and 
                    self._should_include_field(key, value)):
                    formatted_record[key] = value
                    break
        
        # Second pass: add other important fields (with suffixes we care about)
        important_suffixes = ['_height', '_width', '_type', '_route', '_length', '_severity']
        for key, value in attrs.items():
            if (key not in formatted_record and 
                self._should_include_field(key, value) and
                any(key.lower().endswith(suffix) for suffix in important_suffixes)):
                formatted_record[key] = value
        
        # Add attachment info
        if 'attachments' in record and record['attachments']:
            attachment_count = sum(len(files) for files in record['attachments'].values() if files)
            if attachment_count > 0:
                formatted_record['attachment_count'] = attachment_count
                
                # Extract attachment details
                attachments_detail = []
                for category, files in record['attachments'].items():
                    if files:
                        for file in files:
                            attachments_detail.append({
                                'category': category,
                                'name': file.get('name', 'Unknown')
                            })
                formatted_record['attachments'] = attachments_detail
        
        return formatted_record
    
    def _extract_repeats(self, repeats: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Extract and format repeat records"""
        if not repeats:
            return {}
        
        formatted_repeats = {}
        
        for table_name, records in repeats.items():
            if not records:
                continue
            
            formatted_records = []
            for i, record in enumerate(records, 1):
                formatted_record = self._format_record(record, i)
                formatted_records.append(formatted_record)
            
            formatted_repeats[table_name] = {
                'record_count': len(formatted_records),
                'records': formatted_records
            }
        
        return formatted_repeats
    
    def _extract_attachments(self, attachments: Dict[str, List[Dict]]) -> Dict[str, List[str]]:
        """Extract site-level attachments"""
        if not attachments:
            return {}
        
        formatted_attachments = {}
        
        for category, files in attachments.items():
            if files:
                formatted_attachments[category] = [
                    file.get('name', 'Unknown') for file in files
                ]
        
        return formatted_attachments
    
    def parse(self, survey_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse survey data and extract important information.
        
        Args:
            survey_data: The complete survey JSON payload
            
        Returns:
            Dict containing parsed and formatted survey data
        """
        feature = survey_data.get('feature', {})
        
        if not feature:
            return {'error': 'No feature data found in payload'}
        
        attrs = feature.get('attributes', {})
        
        # Build parsed output
        parsed_output = {
            'site_info': self._extract_site_info(attrs),
            'location': self._extract_location(feature.get('geometry', {})),
        }
        
        # Add site-level attachments if present
        if 'attachments' in feature and feature['attachments']:
            parsed_output['site_attachments'] = self._extract_attachments(feature['attachments'])
        
        # Add all other important attributes not in site_info
        other_attrs = {}
        for key, value in attrs.items():
            if (self._should_include_field(key, value) and 
                key not in parsed_output['site_info']):
                other_attrs[key] = value
        
        if other_attrs:
            parsed_output['additional_attributes'] = other_attrs
        
        # Add repeat records if present
        if 'repeats' in feature and feature['repeats']:
            parsed_output['repeat_records'] = self._extract_repeats(feature['repeats'])
        
        return parsed_output
    
    def parse_and_save(self, survey_data: Dict[str, Any], output_filename: str = None) -> Dict[str, Any]:
        """
        Parse survey data and automatically save to markdown file.
        
        Args:
            survey_data: The complete survey JSON payload
            output_filename: Optional custom filename (default: auto-generated from site ID)
            
        Returns:
            Dict containing parsed survey data and output file path
        """
        # Parse the data
        parsed_data = self.parse(survey_data)
        
        if 'error' in parsed_data:
            return parsed_data
        
        # Generate filename if not provided
        if not output_filename:
            site_id = parsed_data.get('site_info', {}).get('customer_site_id', 'unknown')
            survey_type = parsed_data.get('site_info', {}).get('survey_type', 'survey')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"survey_{site_id}_{survey_type}_{timestamp}.md"
        
        # Ensure .md extension
        if not output_filename.endswith('.md'):
            output_filename += '.md'
        
        # Convert to markdown and save
        markdown_content = self.to_markdown(parsed_data)
        
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            parsed_data['output_file'] = output_filename
            print(f"✓ Parsed survey data saved to: {output_filename}")
            
        except IOError as e:
            parsed_data['error'] = f"Failed to save file: {str(e)}"
        
        return parsed_data
    
    def parse_from_file(self, filepath: str, save_markdown: bool = True, output_filename: str = None) -> Dict[str, Any]:
        """
        Parse survey data from a JSON file and optionally save to markdown.
        
        Args:
            filepath: Path to the JSON file
            save_markdown: Whether to automatically save markdown output (default: True)
            output_filename: Optional custom output filename
            
        Returns:
            Dict containing parsed survey data
        """
        try:
            with open(filepath, 'r') as f:
                survey_data = json.load(f)
            
            if save_markdown:
                return self.parse_and_save(survey_data, output_filename)
            else:
                return self.parse(survey_data)
                
        except FileNotFoundError:
            return {'error': f'File not found: {filepath}'}
        except json.JSONDecodeError as e:
            return {'error': f'Invalid JSON: {str(e)}'}
    
    def to_markdown(self, parsed_data: Dict[str, Any]) -> str:
        """
        Convert parsed data to Markdown format.
        
        Args:
            parsed_data: Output from parse() method
            
        Returns:
            Formatted markdown string
        """
        if 'error' in parsed_data:
            return f"# Error\n\n{parsed_data['error']}"
        
        lines = []
        lines.append("# Survey Data Summary")
        lines.append("")
        
        # Site Details - ALL attributes in one section
        lines.append("## SITE DETAILS")
        lines.append("")
        
        # Add all site_info fields
        for key, value in parsed_data.get('site_info', {}).items():
            readable_key = key.replace('_', ' ').title()
            lines.append(f"**{readable_key}:** {value}  ")
        
        # Add all additional_attributes fields (no separate section)
        if parsed_data.get('additional_attributes'):
            for key, value in parsed_data['additional_attributes'].items():
                readable_key = key.replace('_', ' ').title()
                lines.append(f"**{readable_key}:** {value}  ")
        
        lines.append("")
        
        # Location
        if parsed_data.get('location'):
            lines.append("## LOCATION")
            lines.append("")
            for key, value in parsed_data['location'].items():
                readable_key = key.replace('_', ' ').title()
                lines.append(f"**{readable_key}:** {value}  ")
            lines.append("")
        
        # Site Attachments
        if parsed_data.get('site_attachments'):
            lines.append("## SITE PHOTOS")
            lines.append("")
            for category, files in parsed_data['site_attachments'].items():
                readable_category = category.replace('_', ' ').title()
                lines.append(f"### {readable_category} ({len(files)} file(s))")
                lines.append("")
                for file in files:
                    lines.append(f"- {file}")
                lines.append("")
        
        # Repeat Records
        if parsed_data.get('repeat_records'):
            lines.append("## REPEAT RECORDS")
            lines.append("")
            for table_name, table_data in parsed_data['repeat_records'].items():
                readable_table = table_name.replace('_', ' ').title()
                lines.append(f"### {readable_table}")
                lines.append(f"*{table_data['record_count']} records*")
                lines.append("")
                
                for record in table_data['records']:
                    record_num = record.get('record_number', '?')
                    lines.append(f"#### Record {record_num}")
                    lines.append("")
                    for key, value in record.items():
                        if key == 'attachments':
                            lines.append(f"**Attachments:** {len(value)} file(s)")
                            lines.append("")
                            for att in value:
                                lines.append(f"- *{att['category']}:* {att['name']}")
                        elif key != 'attachment_count' and key != 'record_number':
                            readable_key = key.replace('_', ' ').replace('tia ', '').title()
                            # Truncate long values
                            str_value = str(value)
                            if len(str_value) > 100:
                                str_value = str_value[:97] + "..."
                            lines.append(f"**{readable_key}:** {str_value}  ")
                    lines.append("")
        
        lines.append("---")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        return "\n".join(lines)
    
    def to_readable_text(self, parsed_data: Dict[str, Any]) -> str:
        """
        Convert parsed data to human-readable text format.
        
        Args:
            parsed_data: Output from parse() method
            
        Returns:
            Formatted text string
        """
        if 'error' in parsed_data:
            return f"Error: {parsed_data['error']}"
        
        lines = []
        lines.append("=" * 80)
        lines.append("SURVEY DATA SUMMARY")
        lines.append("=" * 80)
        lines.append("")
        
        # Site Info
        lines.append("SITE DETAILS")
        lines.append("-" * 80)
        for key, value in parsed_data.get('site_info', {}).items():
            readable_key = key.replace('_', ' ').title()
            lines.append(f"{readable_key}: {value}")
        lines.append("")
        
        # Location
        if parsed_data.get('location'):
            lines.append("LOCATION")
            lines.append("-" * 80)
            for key, value in parsed_data['location'].items():
                readable_key = key.replace('_', ' ').title()
                lines.append(f"{readable_key}: {value}")
            lines.append("")
        
        # Site Attachments
        if parsed_data.get('site_attachments'):
            lines.append("SITE PHOTOS")
            lines.append("-" * 80)
            for category, files in parsed_data['site_attachments'].items():
                readable_category = category.replace('_', ' ').title()
                lines.append(f"{readable_category}: {len(files)} file(s)")
                for file in files:
                    lines.append(f"  - {file}")
            lines.append("")
        
        # Additional Attributes
        if parsed_data.get('additional_attributes'):
            lines.append("ADDITIONAL ATTRIBUTES")
            lines.append("-" * 80)
            for key, value in parsed_data['additional_attributes'].items():
                readable_key = key.replace('_', ' ').title()
                lines.append(f"{readable_key}: {value}")
            lines.append("")
        
        # Repeat Records
        if parsed_data.get('repeat_records'):
            lines.append("REPEAT RECORDS")
            lines.append("-" * 80)
            for table_name, table_data in parsed_data['repeat_records'].items():
                readable_table = table_name.replace('_', ' ').title()
                lines.append(f"\n{readable_table}: {table_data['record_count']} records")
                lines.append("")
                
                for record in table_data['records']:
                    record_num = record.pop('record_number', '?')
                    lines.append(f"  Record {record_num}:")
                    for key, value in record.items():
                        if key == 'attachments':
                            lines.append(f"    Attachments: {len(value)} file(s)")
                            for att in value:
                                lines.append(f"      - {att['category']}: {att['name']}")
                        elif key != 'attachment_count':
                            readable_key = key.replace('_', ' ').replace('tia ', '').title()
                            # Truncate long values
                            str_value = str(value)
                            if len(str_value) > 100:
                                str_value = str_value[:97] + "..."
                            lines.append(f"    {readable_key}: {str_value}")
                    lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    # Example 1: Parse from file and auto-save to markdown
    parser = SurveyParser()
    
    # This will automatically create a .md file
    # parsed = parser.parse_from_file('CTI_10105_BostonTurnpikeBolton_CompoundPayload.json')
    # print(f"Output saved to: {parsed.get('output_file', 'N/A')}")
    
    # # Example 2: Parse without saving markdown
    # parsed = parser.parse_from_file('CTI_10105_BostonTurnpikeBolton_CompoundPayload.json', save_markdown=False)
    # print(json.dumps(parsed, indent=2))
    
    # Example 3: Parse and save with custom filename
    parsed = parser.parse_from_file('CTI_10105_BostonTurnpikeBolton_CompoundPayload.json', output_filename='my_custom_report.md')
    
    # Example 4: Parse from dict and save
    # with open('survey.json', 'r') as f:
    #     survey_data = json.load(f)
    # parsed = parser.parse_and_save(survey_data)
    
    # Example 5: Get readable text output (not markdown)
    # readable_output = parser.to_readable_text(parsed)
    # print(readable_output)