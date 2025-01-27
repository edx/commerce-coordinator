import json
from collections import defaultdict
from datetime import datetime
import urllib.parse
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)
import csv
from requests import get

class Command(CommercetoolsAPIClientCommand):
    help = "Verify course attributes between CommerceTools and Course Discovery API"

    def handle(self, *args, **options):
        # Fetch all courses from CommerceTools
        limit = 500
        offset = 0
        courses = []

        while True:
            products_result = self.ct_api_client.base_client.products.query(
                limit=limit,
                offset=offset,
            )
            c = 1
            for course in products_result.results:
                for variant in course.master_data.current.variants:
                    c += 1
                    attributes = self.extract_attributes(variant)
                    courses.append(attributes)
            if products_result.offset + products_result.limit >= products_result.total:
                break
            offset += limit

        print('\n\n\n\n\n len = ', len(courses), '\n\n\n\n\n')


        self.write_attributes_to_csv(courses)

    def extract_attributes(self, variant):
        attributes_dict = {attr.name: attr.value for attr in variant.attributes}
        return {
            "sku": variant.sku,
            "mode": attributes_dict.get("mode"),
            "duration-low": attributes_dict.get("duration-low"),
            "duration-high": attributes_dict.get("duration-high"),
            "effort-low": attributes_dict.get("effort-low"),
            "effort-high": attributes_dict.get("effort-high"),
            "pacing-type": attributes_dict.get("pacing-type"),
            "effort-unit": attributes_dict.get("effort-unit"),
            "duration-unit": attributes_dict.get("duration-unit"),
            "verification-upgrade-deadline": attributes_dict.get("verification-upgrade-deadline"),
            "lob": attributes_dict.get("lob"),
            "bulk-purchasable": attributes_dict.get("bulk-purchasable"),
            "courserun-enrollment-end": attributes_dict.get("courserun-enrollment-end"),
            "courserun-enrollment-start": attributes_dict.get("courserun-enrollment-start"),
            "discovery-url": f"https://discovery.stage.edx.org/api/v1/course_runs/{urllib.parse.quote_plus(variant.sku)}/",
            "primary-subject-area": attributes_dict.get("primary-subject-area"),
            "brand-text": attributes_dict.get("brand-text"),
            "status": attributes_dict.get("status"),
            "courserun-status": attributes_dict.get("courserun-status"),
            "external-ids-product": attributes_dict.get("external-ids-product"),
            "courserun-id": attributes_dict.get("courserun-id"),
            "external-ids-variant": attributes_dict.get("external-ids-variant"),
            "courserun-start": attributes_dict.get("courserun-start"),
            "courserun-end": attributes_dict.get("courserun-end"),
            "courserun-uuid": attributes_dict.get("courserun-uuid"),
            "course-uuid": attributes_dict.get("course-uuid"),
            "url-course": attributes_dict.get("url-course"),
            "date-created": attributes_dict.get("date-created"),
        }

    def write_attributes_to_csv(self, courses):
        keys = courses[0].keys()
        with open('course_attributes.csv', 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(courses)

    # def fetch_course_from_discovery(self, course_run_key):
    #     # Fetch course from Course Discovery API
    #
    #     import urllib.parse
    #     encoded_key = urllib.parse.quote_plus(course_run_key)
    #
    #     headers = {
    #         'Authorization': 'Bearer YOUR_API_TOKEN_HERE'
    #     }
    #     response = get(f"https://discovery.stage.edx.org/api/v1/course_runs/{encoded_key}/", headers=headers)
    #     print(f"\n\n\n\n\nFetching discovery for {course_run_key} and hitting url: ", response.url)
    #     # response = get(f"http://localhost:18381/api/v1/courses/{encoded_key}/")
    #     print('\n\n\n\n\n discovery resp = ', response.json(), '\n\n\n\n\n')
    #
    #     if response.status_code == 200:
    #         return response.json()
    #     return None

    # def verify_course_attributes(self, course_code, variant, discovery_course, discrepancies):
    #     # Verify course attributes
    #     attributes = {
    #         "mode": variant.attributes.get("mode"),
    #         "verification-upgrade-deadline": variant.attributes.get("verification-upgrade-deadline"),
    #         "lob": variant.attributes.get("lob"),
    #         "bulk-purchasable": variant.attributes.get("bulk-purchasable"),
    #         "courserun-enrollment-end": variant.attributes.get("courserun-enrollment-end"),
    #         "courserun-enrollment-start": variant.attributes.get("courserun-enrollment-start"),
    #     }
    #
    #     discovery_attributes = {
    #         "mode": discovery_course.get("mode"),
    #         "verification-upgrade-deadline": discovery_course.get("upgrade_deadline_override") or discovery_course.get("upgrade_deadline"),
    #         "lob": discovery_course.get("lob"),
    #         "bulk-purchasable": bool(discovery_course.get("bulk_purchasable")),
    #         "courserun-enrollment-end": discovery_course.get("enrollment_end"),
    #         "courserun-enrollment-start": discovery_course.get("enrollment_start"),
    #     }
    #
    #     for attr, value in attributes.items():
    #         if value != discovery_attributes[attr]:
    #             discrepancies.append({
    #                 "course_code": course_code,
    #                 "attribute": attr,
    #                 "commercetools_value": value,
    #                 "discovery_value": discovery_attributes[attr]
    #             })
