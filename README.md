# Day 5 - Final Project
Scenario: You've been learning how to automate parts of the FIR Filter IP validation process. But how do you check the validation results?

You are now given a reference chip, `golden`, that you have to compare all units (`impl0` to `impl5`) against. `golden` represents the specifications and by comparing how each unit performs against `golden`, you can now check the compliance of each chip. There are 5 test cases (TC) to do for each chip - it passes if its performance is up to specification, i.e. the same as the `golden` chip.

## Assignment instructions
You will need to test for these features on all the instances:
1. Global enable/disable
2. POR register values
3. Input buffer overflow and clearing
4. Filter bypassing
5. Signal processing

After executing all those tests on every instance, use the provided `validation_report.odt` template and make a report that contains:
- A proof of execution (ex: a screenshot of your script execution)
- A brief analysis on the execution result (ex: register field X does not match with the POR values …)
- A status of the test execution (pass/fail/wip)

Notice how we've been working on some of these tests. For example, we've been working on (1) on the Day 2 assignment, we just haven't compared them against `golden` yet. You can re-use code from the previous assignments. You can also make use of the starter code provided in `main.py`.

The following section describes each testcase further.

**Testcase 1: Global enable/disable**
- Our IP has a global enable signal which needs to be asserted to use the IP. When the global enable signal is de-asserted, the IP is expected to be inactive and will not respond to any stimuli.
- Passing criteria: IP channels except for the common channel is inaccessible when enable is de-asserted

**Testcase 2: POR register values**
- Power-on reset (POR) is mechanism in ICs where a reset signal is asserted when the power is first applied. Registers in the IP we are testing will be reset to their default values when a reset signal is asserted.
- Passing Criteria: All register values after reset matches with the values as specified in por.csv

**Testcase 3: Input buffer overflow and clearing**
- The FIR filter IP has an input buffer that stores sampled input signal when the filter is halted. It can store up to 255 samples before it loses data and can be cleared by setting the right register field.
- Passing Criteria: Input buffer count is correct, the correct register field is set upon overflow, and that the input buffer count can be cleared.

**Testcase 4: Filter bypassing**
- A register field in the instances can be set to bypass signal processing.
- Passing Criteria: Output signal matches exactly with the input signal when the bypass is enabled.

**Testcase 5: Signal processing**
- This is the main feature of the IP. You will need to set the filter’s coefficients and drive its input signal. You will be provided with a .cfg file that specifies the coef. values and enables. You will also be provided with a .vec file that contains values of the input signals to drive.
- Proof of execution requirement: A visualization of the input and output signals
- Passing Criteria: Output signals matches exactly with the output signals from the golden model given the same coefficients and input signals.

## Submitting the assignment
This assignment doesn't have an autograder and will be graded manually. 

Once you are done, don't forget to submit by updating `final-project.py` and pushing the commit.
