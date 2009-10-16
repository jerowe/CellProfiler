'''<b>RescaleIntensity<\b>- Changes intensity range of an image to desired specifications.
<hr>

The intensity of the incoming images are rescaled by one of several
methods. This is especially helpful for converting 12-bit images saved in
16-bit format to the correct range.

'''
#CellProfiler is distributed under the GNU General Public License.
#See the accompanying file LICENSE for details.
#
#Developed by the Broad Institute
#Copyright 2003-2009
#
#Please see the AUTHORS file for credits.
#
#Website: http://www.cellprofiler.org
#
#__version__="$Revision: 6746 $"

import numpy as np

import cellprofiler.cpmodule as cpm
import cellprofiler.cpimage as cpi
import cellprofiler.measurements as cpmeas
import cellprofiler.settings as cps

from cellprofiler.cpmath.filter import stretch

M_STRETCH = 'Stretch each image to use the full intensity range'
M_MANUAL_INPUT_RANGE = 'Choose specific values to be reset to the full intensity range'
M_MANUAL_IO_RANGE = 'Choose specific values to be reset to a custom range'
M_DIVIDE_BY_IMAGE_MINIMUM = "Divide by the image's minimum"
M_DIVIDE_BY_IMAGE_MAXIMUM = "Divide by the image's maximum"
M_DIVIDE_BY_VALUE = 'Divide each image by the same value'
M_DIVIDE_BY_MEASUREMENT = 'Divide each image by a previously calculated value'
M_SCALE_BY_IMAGE_MAXIMUM = "Match the image's maximum to another image's maximum"
M_CONVERT_TO_8_BIT = 'Convert to 8 bit'

M_ALL = [M_STRETCH, M_MANUAL_INPUT_RANGE, M_MANUAL_IO_RANGE, 
         M_DIVIDE_BY_IMAGE_MINIMUM, M_DIVIDE_BY_IMAGE_MAXIMUM,
         M_DIVIDE_BY_VALUE, M_DIVIDE_BY_MEASUREMENT, 
         M_SCALE_BY_IMAGE_MAXIMUM, M_CONVERT_TO_8_BIT]


R_SCALE = 'Scale similarly to others'
R_MASK = 'Mask pixels'
R_SET_TO_ZERO = 'Set to zero'
R_SET_TO_CUSTOM = 'Set to custom value'
R_SET_TO_ONE = 'Set to one'

class RescaleIntensity(cpm.CPModule):

    category="Image Processing"
    variable_revision_number = 1
    
    def create_settings(self):
        self.module_name = "RescaleIntensity"
        self.image_name = cps.ImageNameSubscriber("Select the input image","None", doc = '''What did you call the image to be rescaled?''')
        self.rescaled_image_name = cps.ImageNameProvider("Name the output image","RescaledBlue", doc = '''What do you want to call the rescaled image?''')
        self.rescale_method = cps.Choice('Which rescaling method do you want to use?',
                                         choices=M_ALL, doc='''There are nine options for rescaling the input image: 
                                         <ul><li>Stretch each image to use the full intensity range: Find the minimum and maximum values within the unmasked part of the image 
                                         (or the whole image if there is no mask) and rescale every pixel so that 
                                         the minimum has an intensity of zero and the maximum has an intensity of one.</li>
                                         <li>Choose specific values to be reset to the full intensity range: Pixels are
                                        scaled from their user-specified original range to the range, 0 to 1.
                                        Options are available to handle values outside of the original range.
                                            
                                        To convert 12-bit images saved in 16-bit format to the correct range,
                                        use the range, 0 to 0.0625. The value 0.0625 is equivalent 
                                        to 2^12 divided by 2^16, so it will convert a 16 bit image containing 
                                        only 12 bits of data to the proper range.</li>
                                        <li>Choose specific values to be reset to a custom range: Pixels are scaled from their original range to
                                        the new target range. Options are available to handle values outside
                                        of the original range.</li>
                                        <li>Divide by image's minimum: Divide the intensity value of each pixel by the image's minimum intensity
                                        value so that all pixel intensities are equal to or greater than 1.
                                        You can use the output from this option in CorrectIllumination_Apply.
                                        The image becomes an illumination correction function.</li>
                                        <li>Divide by image's maximum: Divide the intensity value of each pixel by the image's maximum intensity
                                        value so that all pixel intensities are less than or equal to 1.</li>
                                        <li>Divide each image by the same value: Divide the intensity value of each pixel by the value entered.</li>
                                        <li>Divide by each image by a previously calculated value: The intensity value of each pixel is divided by some previously calculated
                                        measurement. This measurement can be the output of some other module
                                        or can be a value loaded by the LoadText module.</li>
                                        <li>Match the image's maximum to another image's maximum: Scale an image so that its maximum value is the same as the maximum value
                                        within the target image.</li>
                                        <li>Convert to 8-bit: Images in CellProfiler are normally stored as a floating point number in
                                        the range of 0 to 1. This option converts these images to class uint8, 
                                        meaning an 8 bit integer in the range of 0 to 255.  This is useful to
                                        reduce the amount of memory required to store the image. Warning: Most
                                        CellProfiler modules require the incoming image to be in the standard 0
                                        to 1 range, so this conversion may cause downstream modules to behave 
                                        unexpectedly.</li></ul>''')
        self.wants_automatic_low = cps.Binary('Do you want to use the minimum intensity value in the image as the lower limit of the intensity range?',
                                              False)
        self.wants_automatic_high = cps.Binary('Do you want to use the maximum intensity value in the image as the upper limit of the intensity range?',
                                               False)
        self.source_low = cps.Float('Enter the lower limit for the intensity range for the original image',0)
        self.source_high = cps.Float('Enter the upper limit for the intensity range for the original image',1)
        self.source_scale = cps.FloatRange('Enter the intensity range for the original image',(0,1))
        self.dest_scale = cps.FloatRange('Enter the desired intensity range for the final image', (0,1))
        self.low_truncation_choice = cps.Choice('How do you want to handle values that are less than the lower limit of the intensity range?',
                                                [R_MASK, R_SET_TO_ZERO, 
                                                 R_SET_TO_CUSTOM, R_SCALE], doc = '''There are four ways to handle values less than the lower limit of the intensity range:
                                                 <ul><li> Mask pixels: Creates a mask for the output image. All pixels below
                                                  the lower limit will be masked out.</li>
                                                  <li>Set to zero: Sets all pixels below the lower limit to zero.</li>
                                                  <li>Set to custom value: Sets all pixels below the lower limit to a custom
                                                  value.</li>
                                                  <li>Scale similarly to others: Scales pixels with values below the lower limit
                                                  using the same offset and divisor as other pixels. The results
                                                  will be less than zero.</li></ul>
                                                  ''')
        self.custom_low_truncation = cps.Float("What custom value should be assigned to pixels with values below the lower limit?",0)
        self.high_truncation_choice = cps.Choice('How do you want to handle values that are greater than the upper limit of the intensity range?',
                                                [R_MASK, R_SET_TO_ONE, 
                                                 R_SET_TO_CUSTOM, R_SCALE])
        self.custom_high_truncation = cps.Float("What custom value should be assigned to pixels with values above the upper limit?",0)
        self.matching_image_name = cps.ImageNameSubscriber("What did you call the image whose maximum you want the rescaled image to match?", "None")
        self.divisor_value = cps.Float("What value should be used as the divisor for the final image?",
                                       1,minval=np.finfo(float).eps)
        self.divisor_measurement = cps.Measurement("What measurement do you want to use as the divisor?",
                                                   lambda : cpmeas.IMAGE)

    def settings(self):
        return [self.image_name, self.rescaled_image_name, self.rescale_method,
                self.wants_automatic_low, self.wants_automatic_high,
                self.source_low, self.source_high,
                self.source_scale, self.dest_scale, self.low_truncation_choice,
                self.custom_low_truncation, self.high_truncation_choice,
                self.custom_high_truncation, self.matching_image_name,
                self.divisor_value, self.divisor_measurement]

    def visible_settings(self):
        result =  [self.image_name, self.rescaled_image_name, 
                   self.rescale_method]
        if self.rescale_method in (M_MANUAL_INPUT_RANGE, M_MANUAL_IO_RANGE):
            result += [self.wants_automatic_low]
            if not self.wants_automatic_low.value:
                if self.wants_automatic_high.value:
                    result += [self.source_low, self.wants_automatic_high]
                else:
                    result += [self.wants_automatic_high, self.source_scale]
            elif not self.wants_automatic_high.value:
                result += [self.wants_automatic_high, self.source_high]
            else:
                result += [self.wants_automatic_high]
        if self.rescale_method == M_MANUAL_IO_RANGE:
            result += [self.dest_scale]
        if self.rescale_method in (M_MANUAL_INPUT_RANGE, M_MANUAL_IO_RANGE):
            result += [self.low_truncation_choice]
            if self.low_truncation_choice.value == R_SET_TO_CUSTOM:
                result += [self.custom_low_truncation]
            result += [self.high_truncation_choice]
            if self.high_truncation_choice.value == R_SET_TO_CUSTOM:
                result += [self.custom_high_truncation]
                
        if self.rescale_method == M_SCALE_BY_IMAGE_MAXIMUM:
            result += [self.matching_image_name]
        elif self.rescale_method == M_DIVIDE_BY_MEASUREMENT:
            result += [self.divisor_measurement]
        elif self.rescale_method == M_DIVIDE_BY_VALUE:
            result += [self.divisor_value]
        return result

    def run(self, workspace):
        input_image = workspace.image_set.get_image(self.image_name.value)
        output_mask = None
        if self.rescale_method == M_STRETCH:
            output_image = self.stretch(input_image)
        elif self.rescale_method == M_MANUAL_INPUT_RANGE:
            output_image, output_mask = self.manual_input_range(input_image)
        elif self.rescale_method == M_MANUAL_IO_RANGE:
            output_image, output_mask = self.manual_io_range(input_image)
        elif self.rescale_method == M_DIVIDE_BY_IMAGE_MINIMUM:
            output_image = self.divide_by_image_minimum(input_image)
        elif self.rescale_method == M_DIVIDE_BY_IMAGE_MAXIMUM:
            output_image = self.divide_by_image_maximum(input_image)
        elif self.rescale_method == M_DIVIDE_BY_VALUE:
            output_image = self.divide_by_value(input_image)
        elif self.rescale_method == M_DIVIDE_BY_MEASUREMENT:
            output_image = self.divide_by_measurement(workspace, input_image)
        elif self.rescale_method == M_SCALE_BY_IMAGE_MAXIMUM:
            output_image = self.scale_by_image_maximum(workspace, input_image)
        elif self.rescale_method == M_CONVERT_TO_8_BIT:
            output_image = self.convert_to_8_bit(input_image)
        if output_mask is not None:
            rescaled_image = cpi.Image(output_image, 
                                       mask = output_mask,
                                       parent_image = input_image,
                                       convert = False)
        else:
            rescaled_image = cpi.Image(output_image,
                                       parent_image = input_image,
                                       convert = False)
        workspace.image_set.add(self.rescaled_image_name.value, rescaled_image)
        if workspace.frame is not None:
            self.display(workspace)
    
    def display(self, workspace):
        '''Display the original and rescaled image'''
        figure = workspace.create_or_find_figure(subplots=(2,1))
        image_set = workspace.image_set
        for image_name, i,j in ((self.image_name, 0,0),
                                (self.rescaled_image_name, 1, 0)):
            image_name = image_name.value
            pixel_data = image_set.get_image(image_name).pixel_data
            if pixel_data.ndim == 2:
                figure.subplot_imshow_grayscale(i,j,pixel_data,
                                                title = image_name,
                                                vmin = 0, vmax = 1)
            else:
                figure.subplot_imshow_color(i,j,pixel_data,
                                            title = image_name,
                                            normalize=False)
    
    def stretch(self, input_image):
        '''Stretch the input image to the range 0:1'''
        if input_image.has_mask:
            return stretch(input_image.pixel_data, input_image.mask)
        else:
            return stretch(input_image.pixel_data)
    
    def manual_input_range(self, input_image):
        '''Stretch the input image from the requested range to 0:1'''
        if self.wants_automatic_low.value and self.wants_automatic_high.value:
            return self.stretch(input_image)
        
        src_min, src_max = self.get_source_range(input_image)
        rescaled_image = ((input_image.pixel_data - src_min) / 
                          (src_max - src_min))
        return self.truncate_values(input_image, rescaled_image, 0, 1)
    
    def manual_io_range(self, input_image):
        '''Stretch the input image using manual input and output values'''

        src_min, src_max = self.get_source_range(input_image)
        rescaled_image = ((input_image.pixel_data - src_min) / 
                          (src_max - src_min))
        dest_min = self.dest_scale.min
        dest_max = self.dest_scale.max
        rescaled_image = rescaled_image * (dest_max-dest_min) + dest_min
        return self.truncate_values(input_image, 
                                    rescaled_image, 
                                    dest_min, dest_max)
    
    def divide_by_image_minimum(self, input_image):
        '''Divide the image by its minimum to get an illumination correction function'''
        
        if input_image.has_mask:
            src_min = np.min(input_image.pixel_data[input_image.mask])
        else:
            src_min = np.min(input_image.pixel_data)
        if src_min != 0:
            rescaled_image = input_image.pixel_data / src_min
        return rescaled_image
    
    def divide_by_image_maximum(self, input_image):
        '''Stretch the input image from 0 to the image maximum'''
        
        if input_image.has_mask:
            src_max = np.max(input_image.pixel_data[input_image.mask])
        else:
            src_max = np.max(input_image.pixel_data)
        if src_max != 0:
            rescaled_image = input_image.pixel_data / src_max
        return rescaled_image
    
    def divide_by_value(self, input_image):
        '''Divide the image by a user-specified value'''
        return input_image.pixel_data / self.divisor_value.value
    
    def divide_by_measurement(self, workspace, input_image):
        '''Divide the image by the value of an image measurement'''
        m = workspace.measurements
        value = m.get_current_image_measurement(self.divisor_measurement.value)
        return input_image.pixel_data / float(value) 
        
    def scale_by_image_maximum(self, workspace, input_image):
        '''Scale the image by the maximum of another image
        
        Find the maximum value within the unmasked region of the input
        and reference image. Multiply by the reference maximum, divide
        by the input maximum to scale the input image to the same
        range as the reference image
        '''
        reference_image = workspace.image_set.get_image(self.matching_image_name.value)
        reference_pixels = reference_image.pixel_data
        if reference_image.has_mask:
            reference_pixels = reference_pixels[reference_image.mask]
        reference_max = np.max(reference_pixels)
        if input_image.has_mask:
            image_max = np.max(input_image.pixel_data[input_image.mask])
        else:
            image_max = np.max(input_image.pixel_data)
        if image_max == 0:
            return input_image.pixel_data
        return input_image.pixel_data * reference_max / image_max
    
    def convert_to_8_bit(self, input_image):
        '''Convert the image data to uint8'''
        return (input_image.pixel_data * 255).astype(np.uint8)
    
    def get_source_range(self, input_image):
        '''Get the source range, accounting for automatically computed values'''
        if self.wants_automatic_low.value or self.wants_automatic_high.value:
            input_pixels = input_image.pixel_data
            if input_image.has_mask:
                input_pixels = input_pixels[input_image.mask]
            if self.wants_automatic_low.value:
                src_min = np.min(input_pixels)
            else:
                src_min = self.source_low.value
            if self.wants_automatic_high.value:
                src_max = np.max(input_pixels)
            else:
                src_max = self.source_high.value
        else:
            src_min = self.source_scale.min
            src_max = self.source_scale.max
        return src_min, src_max
    
    def truncate_values(self, input_image, rescaled_image, target_min, target_max):
        '''Handle out of range values based on user settings
        
        input_image - the original input image
        rescaled_image - the pixel data after scaling
        target_min - values below this are out of range
        target_max - values above this are out of range
        
        returns the truncated pixel data and either a mask or None
        if the user doesn't want to mask out-of-range values
        '''
        
        if (self.low_truncation_choice == R_MASK or
            self.high_truncation_choice == R_MASK):
            if input_image.has_mask:
                mask = input_image.mask.copy()
            else:
                mask = np.ones(rescaled_image.shape,bool)
            if self.low_truncation_choice == R_MASK:
                mask[rescaled_image < target_min] = False
            if self.high_truncation_choice == R_MASK:
                mask[rescaled_image > target_max] = False
        else:
            mask = None
        if self.low_truncation_choice == R_SET_TO_ZERO:
            rescaled_image[rescaled_image < target_min] = 0
        elif self.low_truncation_choice == R_SET_TO_CUSTOM:
            rescaled_image[rescaled_image < target_min] =\
                self.custom_low_truncation.value
        
        if self.high_truncation_choice == R_SET_TO_ONE:
            rescaled_image[rescaled_image > target_max] = 1
        elif self.high_truncation_choice == R_SET_TO_CUSTOM:
            rescaled_image[rescaled_image > target_max] =\
                self.custom_high_truncation.value
        if mask is not None and mask.ndim == 3:
            # Color image -> 3-d mask. Collapse the 3rd dimension
            # so any point is masked if any color fails
            mask = np.all(mask,2)
        return rescaled_image, mask
            
    def backwards_compatibilize(self, setting_values, variable_revision_number, 
                                module_name, from_matlab):
        if from_matlab and variable_revision_number == 4:
            new_setting_values = (setting_values[:2] +
                                  [M_STRETCH, # 2: rescale_method,
                                   cps.NO,    # 3: wants_automatic_low
                                   cps.NO,    # 4: wants_automatic_high
                                   "0",       # 5: source_low
                                   "1",       # 6: source_high 
                                   "0,1",     # 7: source_scale
                                   "0,1",     # 8: dest_scale
                                   R_MASK,    # 9: low_truncation_choice
                                   "0",       # 10: custom_low_truncation
                                   R_MASK,    # 11: high_truncation_choice
                                   "1",       # 12: custom_high_truncation
                                   "None",    # 13: matching_image_name
                                   "1",       # 14: divisor_value
                                   "None"     # 15: divisor_measurement
                                   ])
            code = setting_values[2][0]
            if code.upper() == 'S':
                new_setting_values[2] = M_STRETCH
            elif code.upper() == 'E':
                if setting_values[5] == "0" and setting_values[6] == "1":
                    new_setting_values[2] = M_MANUAL_INPUT_RANGE
                else:
                    new_setting_values[2] = M_MANUAL_IO_RANGE
                if setting_values[3].upper() == "AA":
                    new_setting_values[3] = cps.YES
                    if setting_values[4].upper() == "AA":
                        new_setting_values[4] = cps.YES
                    else:
                        new_setting_values[6] = setting_values[4]
                elif setting_values[4].upper() == "AA":
                    new_setting_values[4] = cps.YES
                    new_setting_values[5] = setting_values[3]
                else:
                    new_setting_values[5] = setting_values[3]
                    new_setting_values[6] = setting_values[4]
                    new_setting_values[7] = ",".join(setting_values[3:5])
                new_setting_values[8] = ",".join(setting_values[5:7])
                new_setting_values[9] = R_SET_TO_CUSTOM
                new_setting_values[10] = setting_values[7]
                new_setting_values[11] = R_SET_TO_CUSTOM
                new_setting_values[12] = setting_values[8]
            elif code.upper() == 'G':
                new_setting_values[2] = M_DIVIDE_BY_IMAGE_MINIMUM
            elif code.upper() == 'M':
                new_setting_values[2] = M_SCALE_BY_IMAGE_MAXIMUM
                new_setting_values[13] = setting_values[9]
            elif code.upper() == 'C':
                new_setting_values[2] = M_CONVERT_TO_8_BIT
            elif code.upper() == 'T':
                new_setting_values[2] = M_DIVIDE_BY_MEASUREMENT
                new_setting_values[15] = setting_values[10]
            setting_values = new_setting_values
            variable_revision_number = 1
            from_matlab = False
        return setting_values, variable_revision_number, from_matlab

